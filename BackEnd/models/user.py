"""User / authentication schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=120)
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        import re

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[@$!%*?&.,#+\-_]", v):
            raise ValueError("Password must contain a special character")
        return v


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False


class LoginResponse(BaseModel):
    status: str
    message: str
    user: UserResponse
    csrf_token: str


class CheckResponse(BaseModel):
    status: str
    authenticated: bool
    user: Optional[UserResponse] = None
    csrf_token: Optional[str] = None


__all__ = [
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserInDB",
    "UserResponse",
    "LoginRequest",
    "LoginResponse",
    "CheckResponse",
]
