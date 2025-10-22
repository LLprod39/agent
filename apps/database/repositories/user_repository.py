"""User repository for user management."""

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: str = "viewer",
    ) -> User:
        """Create a new user."""
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=True,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        logger.info(f"Created user {username} with role {role}")
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_users(self, active_only: bool = True) -> List[User]:
        """List all users."""
        query = select(User)
        if active_only:
            query = query.where(User.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())
