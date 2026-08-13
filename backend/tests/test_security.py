from app.core.security import hash_password, verify_password


def test_hash_password_non_plaintext():
    """Verify password hashing produces a non-plaintext Argon2id hash."""
    plain = "MySecretPassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert plain not in hashed
    assert hashed.startswith("$argon2id$")


def test_hash_password_unique_salts():
    """Verify hashing the same password twice produces different hashes due to unique salts."""
    plain = "SamePassword123!"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)

    assert hash1 != hash2
    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True


def test_verify_password_success():
    """Verify correct password passes verification."""
    plain = "CorrectPassword456!"
    hashed = hash_password(plain)

    assert verify_password(plain, hashed) is True


def test_verify_password_incorrect():
    """Verify incorrect password fails verification."""
    plain = "CorrectPassword456!"
    hashed = hash_password(plain)

    assert verify_password("WrongPassword789!", hashed) is False


def test_verify_password_invalid_or_malformed_hash():
    """Verify invalid or malformed hash inputs are safely handled without throwing exceptions."""
    plain = "Password123!"

    assert verify_password(plain, "not_a_valid_hash") is False
    assert verify_password(plain, "$argon2id$v=19$m=65536,t=3,p=4$invalid$invalid") is False
    assert verify_password(plain, "") is False
    assert verify_password(plain, None) is False


def test_create_and_decode_access_token():
    """Verify JWT access token creation and payload decoding."""
    from datetime import timedelta
    from app.core.security import create_access_token, decode_access_token

    token, expires_in = create_access_token(subject=42, expires_delta=timedelta(minutes=15))

    assert isinstance(token, str)
    assert expires_in == 15 * 60

    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload
    assert "iat" in payload
