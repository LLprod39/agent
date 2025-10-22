"""Integration tests for database functionality."""

import asyncio
import unittest
from datetime import datetime

from apps.database.connection import DatabaseManager
from apps.database.migrations import MigrationManager
from apps.database.repositories import (
    TaskRepository,
    UserRepository,
    SessionRepository,
    MessageRepository,
    AuditLogRepository,
)
from apps.database.models import TaskStatus, MessageRole
from config.settings import get_settings


class DatabaseIntegrationTests(unittest.TestCase):
    """Integration tests for database operations."""

    @classmethod
    def setUpClass(cls):
        """Set up database for tests."""
        cls.settings = get_settings()
        # Use test database URL if available
        cls.db_url = cls.settings.database_url.replace(
            "/devops_agent", "/devops_agent_test"
        )

    def setUp(self):
        """Set up test database."""
        self.db_manager = None
        self.session = None

    async def async_setup(self):
        """Async setup for database."""
        self.db_manager = DatabaseManager(self.db_url, echo=False)
        await self.db_manager.initialize()

        # Run migrations
        migration_manager = MigrationManager(self.db_manager.engine)
        await migration_manager.migrate()

        # Get session
        async for session in self.db_manager.get_session():
            self.session = session
            break

    async def async_teardown(self):
        """Async teardown for database."""
        if self.db_manager:
            await self.db_manager.close()

    def test_database_connection(self):
        """Test database connection and initialization."""

        async def test():
            await self.async_setup()
            
            # Check health
            health = await self.db_manager.health_check()
            self.assertTrue(health)
            
            await self.async_teardown()

        asyncio.run(test())

    def test_user_repository(self):
        """Test user repository operations."""

        async def test():
            await self.async_setup()
            
            repo = UserRepository(self.session)

            # Create user
            user = await repo.create(
                username="test_user",
                email="test@example.com",
                hashed_password="hashed_password_123",
            )
            self.assertIsNotNone(user)
            self.assertEqual(user.username, "test_user")
            self.assertEqual(user.email, "test@example.com")

            # Get by username
            found_user = await repo.get_by_username("test_user")
            self.assertIsNotNone(found_user)
            self.assertEqual(found_user.id, user.id)

            # Get by email
            found_user = await repo.get_by_email("test@example.com")
            self.assertIsNotNone(found_user)
            self.assertEqual(found_user.id, user.id)

            # Update user
            updated = await repo.update(str(user.id), is_active=False)
            self.assertFalse(updated.is_active)

            # Delete user
            deleted = await repo.delete(str(user.id))
            self.assertTrue(deleted)
            
            await self.async_teardown()

        asyncio.run(test())

    def test_task_repository(self):
        """Test task repository operations."""

        async def test():
            await self.async_setup()
            
            # Create user first
            user_repo = UserRepository(self.session)
            user = await user_repo.create(
                username="task_user",
                email="task@example.com",
                hashed_password="password",
            )

            task_repo = TaskRepository(self.session)

            # Create task
            task = await task_repo.create(
                user_id=str(user.id),
                title="Test Task",
                description="This is a test task",
                environment_profile="dev-k8s",
                metadata={"test": "data"},
            )
            self.assertIsNotNone(task)
            self.assertEqual(task.title, "Test Task")
            self.assertEqual(task.status, TaskStatus.PENDING)

            # Update task status
            updated = await task_repo.update_status(
                str(task.id), TaskStatus.IN_PROGRESS
            )
            self.assertEqual(updated.status, TaskStatus.IN_PROGRESS)
            self.assertIsNotNone(updated.started_at)

            # Complete task
            completed = await task_repo.update_status(
                str(task.id), TaskStatus.COMPLETED
            )
            self.assertEqual(completed.status, TaskStatus.COMPLETED)
            self.assertIsNotNone(completed.completed_at)

            # Get user tasks
            tasks = await task_repo.get_user_tasks(str(user.id))
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].id, task.id)

            # Cleanup
            await user_repo.delete(str(user.id))
            
            await self.async_teardown()

        asyncio.run(test())

    def test_audit_log_repository(self):
        """Test audit log repository operations."""

        async def test():
            await self.async_setup()
            
            # Create user
            user_repo = UserRepository(self.session)
            user = await user_repo.create(
                username="audit_user",
                email="audit@example.com",
                hashed_password="password",
            )

            audit_repo = AuditLogRepository(self.session)

            # Create audit log
            log = await audit_repo.create(
                action="task_created",
                resource_type="task",
                user_id=str(user.id),
                resource_id="task-123",
                details={"description": "Created test task"},
                ip_address="127.0.0.1",
            )
            self.assertIsNotNone(log)
            self.assertEqual(log.action, "task_created")
            self.assertEqual(log.resource_type, "task")

            # Get user logs
            logs = await audit_repo.get_user_logs(str(user.id))
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].id, log.id)

            # Get recent logs
            recent = await audit_repo.get_recent_logs(limit=10)
            self.assertGreaterEqual(len(recent), 1)

            # Cleanup
            await user_repo.delete(str(user.id))
            
            await self.async_teardown()

        asyncio.run(test())

    def test_session_and_messages(self):
        """Test session and message repository operations."""

        async def test():
            await self.async_setup()
            
            # Create user
            user_repo = UserRepository(self.session)
            user = await user_repo.create(
                username="session_user",
                email="session@example.com",
                hashed_password="password",
            )

            # Create session
            session_repo = SessionRepository(self.session)
            session = await session_repo.create(
                user_id=str(user.id),
                name="Test Session",
                environment_profile="dev-k8s",
            )
            self.assertIsNotNone(session)
            self.assertTrue(session.is_active)

            # Create messages
            message_repo = MessageRepository(self.session)
            msg1 = await message_repo.create(
                session_id=str(session.id),
                role=MessageRole.USER,
                content="Hello, agent!",
                metadata={"source": "test"},
            )
            msg2 = await message_repo.create(
                session_id=str(session.id),
                role=MessageRole.ASSISTANT,
                content="Hello! How can I help?",
            )

            # Get session messages
            messages = await message_repo.get_session_messages(str(session.id))
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].content, "Hello, agent!")
            self.assertEqual(messages[1].content, "Hello! How can I help?")

            # Get recent messages
            recent = await message_repo.get_recent_messages(str(session.id), count=1)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0].content, "Hello! How can I help?")

            # Deactivate session
            deactivated = await session_repo.deactivate(str(session.id))
            self.assertTrue(deactivated)

            # Cleanup
            await user_repo.delete(str(user.id))
            
            await self.async_teardown()

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
