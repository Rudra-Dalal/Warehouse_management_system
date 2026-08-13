from datetime import timedelta
import pytest
import jwt

from commons.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verifies bcrypt password hashing and verification functionality.
    Ensures correct password returns True and wrong password returns False.
    """
    raw_password = "SecurePassword123!"
    hashed_password = hash_password(raw_password)

    assert hashed_password != raw_password
    assert verify_password(raw_password, hashed_password) is True
    assert verify_password("WrongPassword123!", hashed_password) is False


def test_jwt_token_creation_and_decoding():
    """Verifies JWT token encoding and decoding claim extraction.
    Ensures subject claims and timestamps match.
    """
    user_id = "65c3b1a2f91a2b3c4d5e6f7a"
    token = create_access_token(subject=user_id)

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert "exp" in payload


def test_jwt_token_expiration():
    """Verifies expired JWT access token raises ExpiredSignatureError exception."""
    user_id = "65c3b1a2f91a2b3c4d5e6f7a"
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_invalid_jwt_signature():
    """Verifies JWT access token with invalid signature raises PyJWTError exception."""
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature"

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(invalid_token)
