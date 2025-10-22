"""Authentication router for login, registration, etc."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.middleware.auth import (
    auth_service,
    get_current_user,
    get_current_active_user,
)
from apps.database.session import get_db_session
from apps.database.repositories import UserRepository, AuditRepository
from apps.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response models
class UserCreate(BaseModel):
    """User registration request."""

    username: str
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    """User login request."""

    username: str
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Check if username already exists
    existing_user = await user_repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    existing_email = await user_repo.get_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = auth_service.get_password_hash(user_data.password)

    # Create user (first user is admin, others are viewer by default)
    all_users = await user_repo.list_users(active_only=False)
    role = "admin" if len(all_users) == 0 else "viewer"

    user = await user_repo.create(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=role,
    )

    # Log registration
    await audit_repo.log(
        action="user_registered",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        details={"username": user.username, "role": role},
        status="success",
    )

    logger.info(f"New user registered: {user.username} (role: {role})")
    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """Login and get JWT token."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Get user
    user = await user_repo.get_by_username(credentials.username)

    if not user:
        await audit_repo.log(
            action="login_failed",
            resource_type="user",
            details={"username": credentials.username, "reason": "user_not_found"},
            status="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Verify password
    if not auth_service.verify_password(credentials.password, user.hashed_password):
        await audit_repo.log(
            action="login_failed",
            resource_type="user",
            user_id=user.id,
            details={"username": credentials.username, "reason": "invalid_password"},
            status="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if user is active
    if not user.is_active:
        await audit_repo.log(
            action="login_failed",
            resource_type="user",
            user_id=user.id,
            details={"username": credentials.username, "reason": "inactive_user"},
            status="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create access token
    access_token = auth_service.create_access_token(data={"sub": user.username})

    # Log successful login
    await audit_repo.log(
        action="user_logged_in",
        resource_type="user",
        user_id=user.id,
        details={"username": user.username},
        status="success",
    )

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_session),
):
    """Logout (invalidate token - client-side)."""
    audit_repo = AuditRepository(db)

    await audit_repo.log(
        action="user_logged_out",
        resource_type="user",
        user_id=current_user.id,
        details={"username": current_user.username},
        status="success",
    )

    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}
