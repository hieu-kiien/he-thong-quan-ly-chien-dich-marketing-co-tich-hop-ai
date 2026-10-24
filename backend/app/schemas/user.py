from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.schemas.common import InputModel, ORMModel


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginIn(InputModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class TokenOut(ORMModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(InputModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class UserCreate(InputModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class UserUpdate(InputModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class ResetPasswordIn(InputModel):
    new_password: str = Field(min_length=1, max_length=128)


class UserFilters(InputModel):
    q: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
