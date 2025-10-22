"""Authentication service for user management."""

import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.repositories import UserRepository
from .jwt_handler import JWTHandler

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    def __init__(self, jwt_handler: JWTHandler):
        self.jwt_handler = jwt_handler

    async def register_user(
        self, session: AsyncSession, username: str, email: str, password: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Register a new user."""
        try:
            user_repo = UserRepository(session)

            # Check if user already exists
            existing_user = await user_repo.get_by_username(username)
            if existing_user:
                return None, "Username already exists"

            existing_email = await user_repo.get_by_email(email)
            if existing_email:
                return None, "Email already exists"

            # Hash password
            hashed_password = self.jwt_handler.hash_password(password)

            # Create user
            user = await user_repo.create(username, email, hashed_password)

            # Create tokens
            tokens = self.jwt_handler.create_token_pair(
                str(user.id), user.username, user.is_admin
            )

            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                },
                "tokens": tokens,
            }, None

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return None, "Registration failed"

    async def authenticate_user(
        self, session: AsyncSession, username: str, password: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Authenticate user with username and password."""
        try:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_username(username)
            if not user:
                return None, "Invalid credentials"

            # Check if user is active
            if not user.is_active:
                return None, "Account is disabled"

            # Verify password
            if not self.jwt_handler.verify_password(password, user.hashed_password):
                return None, "Invalid credentials"

            # Create tokens
            tokens = self.jwt_handler.create_token_pair(
                str(user.id), user.username, user.is_admin
            )

            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                },
                "tokens": tokens,
            }, None

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None, "Authentication failed"

    async def refresh_tokens(
        self, refresh_token: str
    ) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Refresh access token using refresh token."""
        try:
            new_tokens = self.jwt_handler.refresh_access_token(refresh_token)
            if not new_tokens:
                return None, "Invalid refresh token"

            return new_tokens, None

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None, "Token refresh failed"

    async def get_current_user(
        self, session: AsyncSession, token: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get current user from token."""
        try:
            # Verify token and get user info
            user_info = self.jwt_handler.get_user_from_token(token)
            if not user_info:
                return None, "Invalid token"

            # Get user from database
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_info["user_id"])
            if not user:
                return None, "User not found"

            if not user.is_active:
                return None, "Account is disabled"

            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat(),
            }, None

        except Exception as e:
            logger.error(f"Get current user failed: {e}")
            return None, "Authentication failed"

    async def change_password(
        self,
        session: AsyncSession,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """Change user password."""
        try:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_id(user_id)
            if not user:
                return False, "User not found"

            # Verify current password
            if not self.jwt_handler.verify_password(
                current_password, user.hashed_password
            ):
                return False, "Current password is incorrect"

            # Hash new password
            hashed_password = self.jwt_handler.hash_password(new_password)

            # Update password
            await user_repo.update(user_id, hashed_password=hashed_password)

            return True, None

        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return False, "Password change failed"

    async def update_profile(
        self, session: AsyncSession, user_id: str, email: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Update user profile."""
        try:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_id(user_id)
            if not user:
                return None, "User not found"

            # Check if email is already taken
            if email and email != user.email:
                existing_user = await user_repo.get_by_email(email)
                if existing_user:
                    return None, "Email already exists"

            # Update user
            update_data = {}
            if email:
                update_data["email"] = email

            if update_data:
                updated_user = await user_repo.update(user_id, **update_data)
                if not updated_user:
                    return None, "Update failed"
            else:
                updated_user = user

            return {
                "id": str(updated_user.id),
                "username": updated_user.username,
                "email": updated_user.email,
                "is_admin": updated_user.is_admin,
                "created_at": updated_user.created_at.isoformat(),
                "updated_at": updated_user.updated_at.isoformat(),
            }, None

        except Exception as e:
            logger.error(f"Profile update failed: {e}")
            return None, "Profile update failed"

    async def deactivate_user(
        self, session: AsyncSession, user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Deactivate user account."""
        try:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_id(user_id)
            if not user:
                return False, "User not found"

            # Deactivate user
            await user_repo.update(user_id, is_active=False)

            return True, None

        except Exception as e:
            logger.error(f"User deactivation failed: {e}")
            return False, "User deactivation failed"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token and return payload."""
        return self.jwt_handler.verify_access_token(token)

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user information from token."""
        return self.jwt_handler.get_user_from_token(token)
