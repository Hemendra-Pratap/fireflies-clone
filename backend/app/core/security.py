"""Password security module using Argon2id."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

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
