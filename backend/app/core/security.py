from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with unique salt generation."""
    if not isinstance(plain_password, str):
        raise TypeError("Password must be a string")
    return _ph.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.
    
    Returns True if the password matches, False if mismatch or invalid hash format.
    """
    if not isinstance(plain_password, str) or not isinstance(password_hash, str):
        return False
    if not password_hash:
        return False

    try:
        return _ph.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHashError, VerificationError, TypeError, ValueError):
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Create a signed JWT access token.
    
    Returns tuple of (encoded_jwt_token_str, expires_in_seconds).
    """
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire_dt = now + expires_delta
    else:
        expire_dt = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expires_in_seconds = int((expire_dt - now).total_seconds())

    to_encode = {
        "sub": str(subject),
        "exp": expire_dt,
        "iat": now,
    }

    token = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in_seconds


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
