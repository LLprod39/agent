"""JWT token handling for authentication."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class JWTHandler:
    """JWT token handler."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "type": "access"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create refresh token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """Verify and decode token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("type") != token_type:
                logger.warning(
                    f"Invalid token type: expected {token_type}, got {payload.get('type')}"
                )
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                logger.warning("Token missing expiration")
                return None

            if datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning("Token expired")
                return None

            return payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify access token."""
        return self.verify_token(token, "access")

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify refresh token."""
        return self.verify_token(token, "refresh")

    def hash_password(self, password: str) -> str:
        """Hash password."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_token_pair(
        self, user_id: str, username: str, is_admin: bool = False
    ) -> Dict[str, str]:
        """Create access and refresh token pair."""
        token_data = {"sub": user_id, "username": username, "is_admin": is_admin}

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Create new access token from refresh token."""
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        # Create new access token with same data
        token_data = {
            "sub": payload.get("sub"),
            "username": payload.get("username"),
            "is_admin": payload.get("is_admin", False),
        }

        access_token = self.create_access_token(token_data)

        return {"access_token": access_token, "token_type": "bearer"}

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information from token."""
        payload = self.verify_access_token(token)
        if not payload:
            return None

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "is_admin": payload.get("is_admin", False),
        }
