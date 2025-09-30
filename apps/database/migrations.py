"""Database migrations for the DevOps LLM Agent."""

import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class Migration:
    """Base migration class."""

    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description

    async def up(self, engine: AsyncEngine) -> None:
        """Apply migration."""
        raise NotImplementedError

    async def down(self, engine: AsyncEngine) -> None:
        """Rollback migration."""
        raise NotImplementedError


class CreateMigrationsTable(Migration):
    """Create migrations table."""

    def __init__(self):
        super().__init__("001", "Create migrations table")

    async def up(self, engine: AsyncEngine) -> None:
        """Create migrations table."""
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

    async def down(self, engine: AsyncEngine) -> None:
        """Drop migrations table."""
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS migrations"))


class AddUserIndexes(Migration):
    """Add additional indexes for users table."""

    def __init__(self):
        super().__init__("002", "Add user indexes")

    async def up(self, engine: AsyncEngine) -> None:
        """Add indexes."""
        async with engine.begin() as conn:
            # Add composite index for user lookup
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_users_username_active 
                ON users (username, is_active)
            """)
            )

            # Add index for email lookup
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_users_email_active 
                ON users (email, is_active)
            """)
            )

    async def down(self, engine: AsyncEngine) -> None:
        """Remove indexes."""
        async with engine.begin() as conn:
            await conn.execute(text("DROP INDEX IF EXISTS idx_users_username_active"))
            await conn.execute(text("DROP INDEX IF EXISTS idx_users_email_active"))


class AddTaskPerformanceIndexes(Migration):
    """Add performance indexes for tasks."""

    def __init__(self):
        super().__init__("003", "Add task performance indexes")

    async def up(self, engine: AsyncEngine) -> None:
        """Add performance indexes."""
        async with engine.begin() as conn:
            # Add index for task status and user
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_status_created 
                ON tasks (user_id, status, created_at)
            """)
            )

            # Add index for task completion time
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_tasks_completed_at 
                ON tasks (completed_at) WHERE completed_at IS NOT NULL
            """)
            )

    async def down(self, engine: AsyncEngine) -> None:
        """Remove indexes."""
        async with engine.begin() as conn:
            await conn.execute(
                text("DROP INDEX IF EXISTS idx_tasks_user_status_created")
            )
            await conn.execute(text("DROP INDEX IF EXISTS idx_tasks_completed_at"))


class AddLLMUsagePartitioning(Migration):
    """Add partitioning for LLM usage table."""

    def __init__(self):
        super().__init__("004", "Add LLM usage partitioning")

    async def up(self, engine: AsyncEngine) -> None:
        """Add partitioning."""
        async with engine.begin() as conn:
            # Create partitioned table (PostgreSQL specific)
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS llm_usage_partitioned (
                    LIKE llm_usage INCLUDING ALL
                ) PARTITION BY RANGE (created_at)
            """)
            )

            # Create monthly partitions for the next 12 months
            from datetime import datetime, timedelta

            base_date = datetime.utcnow().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

            for i in range(12):
                start_date = base_date + timedelta(days=30 * i)
                end_date = start_date + timedelta(days=30)

                partition_name = f"llm_usage_{start_date.strftime('%Y_%m')}"

                await conn.execute(
                    text(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} 
                    PARTITION OF llm_usage_partitioned
                    FOR VALUES FROM ('{start_date.isoformat()}') 
                    TO ('{end_date.isoformat()}')
                """)
                )

    async def down(self, engine: AsyncEngine) -> None:
        """Remove partitioning."""
        async with engine.begin() as conn:
            await conn.execute(
                text("DROP TABLE IF EXISTS llm_usage_partitioned CASCADE")
            )


class AddAuditLogRetention(Migration):
    """Add audit log retention policy."""

    def __init__(self):
        super().__init__("005", "Add audit log retention policy")

    async def up(self, engine: AsyncEngine) -> None:
        """Add retention policy."""
        async with engine.begin() as conn:
            # Create function to clean old audit logs
            await conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION clean_old_audit_logs()
                RETURNS void AS $$
                BEGIN
                    DELETE FROM audit_logs 
                    WHERE created_at < NOW() - INTERVAL '90 days';
                END;
                $$ LANGUAGE plpgsql;
            """)
            )

            # Create index for efficient deletion
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
                ON audit_logs (created_at)
            """)
            )

    async def down(self, engine: AsyncEngine) -> None:
        """Remove retention policy."""
        async with engine.begin() as conn:
            await conn.execute(text("DROP FUNCTION IF EXISTS clean_old_audit_logs()"))
            await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_created_at"))


class MigrationManager:
    """Migration manager."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.migrations: List[Migration] = [
            CreateMigrationsTable(),
            AddUserIndexes(),
            AddTaskPerformanceIndexes(),
            AddLLMUsagePartitioning(),
            AddAuditLogRetention(),
        ]

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text("""
                    SELECT version FROM migrations ORDER BY version
                """)
                )
                return [row[0] for row in result]
        except Exception:
            # Table doesn't exist yet
            return []

    async def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration."""
        logger.info(f"Applying migration {migration.version}: {migration.description}")

        async with self.engine.begin() as conn:
            # Apply migration
            await migration.up(self.engine)

            # Record migration
            await conn.execute(
                text("""
                INSERT INTO migrations (version, description) 
                VALUES (:version, :description)
            """),
                {"version": migration.version, "description": migration.description},
            )

        logger.info(f"Migration {migration.version} applied successfully")

    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback a single migration."""
        logger.info(
            f"Rolling back migration {migration.version}: {migration.description}"
        )

        async with self.engine.begin() as conn:
            # Rollback migration
            await migration.down(self.engine)

            # Remove migration record
            await conn.execute(
                text("""
                DELETE FROM migrations WHERE version = :version
            """),
                {"version": migration.version},
            )

        logger.info(f"Migration {migration.version} rolled back successfully")

    async def migrate(self) -> None:
        """Apply all pending migrations."""
        applied_migrations = await self.get_applied_migrations()

        for migration in self.migrations:
            if migration.version not in applied_migrations:
                await self.apply_migration(migration)

    async def rollback(self, target_version: str) -> None:
        """Rollback to target version."""
        applied_migrations = await self.get_applied_migrations()

        # Rollback in reverse order
        for migration in reversed(self.migrations):
            if (
                migration.version in applied_migrations
                and migration.version > target_version
            ):
                await self.rollback_migration(migration)

    async def status(self) -> Dict[str, Any]:
        """Get migration status."""
        applied_migrations = await self.get_applied_migrations()

        return {
            "total_migrations": len(self.migrations),
            "applied_migrations": len(applied_migrations),
            "pending_migrations": len(self.migrations) - len(applied_migrations),
            "applied": applied_migrations,
            "pending": [
                migration.version
                for migration in self.migrations
                if migration.version not in applied_migrations
            ],
        }
