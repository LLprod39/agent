"""Authentication middleware for FastAPI."""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from .auth_service import AuthService

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Authentication middleware."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ) -> Dict[str, Any]:
        """Get current authenticated user."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user, error = await self.auth_service.get_current_user(
            session, credentials.credentials
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error or "Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    async def get_current_user_optional(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ) -> Optional[Dict[str, Any]]:
        """Get current user if authenticated, otherwise None."""
        if not credentials:
            return None

        try:
            user, error = await self.auth_service.get_current_user(
                session, credentials.credentials
            )
            return user if user else None
        except Exception:
            return None

    async def get_current_admin_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ) -> Dict[str, Any]:
        """Get current authenticated admin user."""
        user = await self.get_current_user(credentials, session)

        if not user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )

        return user

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token without database lookup."""
        return self.auth_service.verify_token(token)

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user info from token without database lookup."""
        return self.auth_service.get_user_from_token(token)


# Dependency functions for FastAPI
def get_auth_middleware(auth_service: AuthService) -> AuthMiddleware:
    """Get authentication middleware instance."""
    return AuthMiddleware(auth_service)


def get_current_user_dependency(auth_service: AuthService):
    """Get current user dependency."""
    middleware = get_auth_middleware(auth_service)
    return middleware.get_current_user


def get_current_user_optional_dependency(auth_service: AuthService):
    """Get current user optional dependency."""
    middleware = get_auth_middleware(auth_service)
    return middleware.get_current_user_optional


def get_current_admin_user_dependency(auth_service: AuthService):
    """Get current admin user dependency."""
    middleware = get_auth_middleware(auth_service)
    return middleware.get_current_admin_user
