"""Authentication routers for FastAPI."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from ..database.connection import get_db_session
from .auth_service import AuthService
from .middleware import security

logger = logging.getLogger(__name__)


# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ProfileUpdate(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    user: Dict[str, Any]
    tokens: Dict[str, str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool
    created_at: str


def create_auth_router(auth_service: AuthService) -> APIRouter:
    """Create authentication router."""
    router = APIRouter(prefix="/auth", tags=["authentication"])

    @router.post("/register", response_model=AuthResponse)
    async def register(
        user_data: UserRegister, session: AsyncSession = Depends(get_db_session)
    ):
        """Register a new user."""
        user, error = await auth_service.register_user(
            session, user_data.username, user_data.email, user_data.password
        )

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        return AuthResponse(**user)

    @router.post("/login", response_model=AuthResponse)
    async def login(
        login_data: UserLogin, session: AsyncSession = Depends(get_db_session)
    ):
        """Authenticate user and return tokens."""
        user, error = await auth_service.authenticate_user(
            session, login_data.username, login_data.password
        )

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        return AuthResponse(**user)

    @router.post("/refresh", response_model=TokenResponse)
    async def refresh_token(token_data: TokenRefresh):
        """Refresh access token."""
        tokens, error = await auth_service.refresh_tokens(token_data.refresh_token)

        if not tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        return TokenResponse(**tokens)

    @router.get("/me", response_model=UserResponse)
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ):
        """Get current user information."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user, error = await auth_service.get_current_user(
            session, credentials.credentials
        )

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        return UserResponse(**user)

    @router.put("/password")
    async def change_password(
        password_data: PasswordChange,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ):
        """Change user password."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get current user
        user, error = await auth_service.get_current_user(
            session, credentials.credentials
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        success, error = await auth_service.change_password(
            session,
            user["id"],
            password_data.current_password,
            password_data.new_password,
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        return {"message": "Password changed successfully"}

    @router.put("/profile", response_model=UserResponse)
    async def update_profile(
        profile_data: ProfileUpdate,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ):
        """Update user profile."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get current user
        user, error = await auth_service.get_current_user(
            session, credentials.credentials
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        updated_user, error = await auth_service.update_profile(
            session, user["id"], email=profile_data.email
        )

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        return UserResponse(**updated_user)

    @router.delete("/account")
    async def deactivate_account(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ):
        """Deactivate user account."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get current user
        user, error = await auth_service.get_current_user(
            session, credentials.credentials
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        success, error = await auth_service.deactivate_user(session, user["id"])

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        return {"message": "Account deactivated successfully"}

    return router
