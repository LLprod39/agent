"""Database connection and session management."""

import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager."""

    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        self.echo = echo
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                poolclass=NullPool,  # Use NullPool for async
                future=True,
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


async def initialize_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """Initialize the global database manager."""
    global db_manager
    db_manager = DatabaseManager(database_url, echo)
    await db_manager.initialize()
    return db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    manager = await get_database_manager()
    async for session in manager.get_session():
        yield session
