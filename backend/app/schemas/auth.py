from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import TimestampedModel


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User's valid email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strip surrounding whitespace and convert email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserRead(TimestampedModel):
    """Schema for returning user data. Never includes password or password_hash."""

    id: int
    email: str


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User's registered email address")
    password: str = Field(..., min_length=1, description="User's password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strip surrounding whitespace and convert email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TokenResponse(BaseModel):
    """Schema for returning JWT access token."""

    access_token: str = Field(..., description="JWT access token string")
    token_type: str = Field("bearer", description="Token type, defaults to bearer")
    expires_in: int = Field(..., description="Access token expiration duration in seconds")
