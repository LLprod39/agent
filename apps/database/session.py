"""Database session management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from apps.api.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Manages database sessions and connections."""

    def __init__(self):
        self.settings = get_settings()
        self._engine = None
        self._session_maker = None

    def initialize(self):
        """Initialize database engine and session maker."""
        logger.info(f"Initializing database connection to {self.settings.database_url}")

        # Convert postgres:// to postgresql+asyncpg://
        database_url = self.settings.database_url
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self._engine = create_async_engine(
            database_url,
            echo=self.settings.api_debug,
            poolclass=NullPool,  # Disable pooling for async
            future=True,
        )

        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Database initialized successfully")

    async def close(self):
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if self._session_maker is None:
            raise RuntimeError("DatabaseSessionManager not initialized. Call initialize() first.")

        async with self._session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()


# Global session manager instance
db_manager = DatabaseSessionManager()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database session."""
    async with db_manager.session() as session:
        yield session
