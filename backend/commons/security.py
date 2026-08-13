from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt

from commons.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


def hash_password(plain_password: str) -> str:
    """Hashes a plaintext password string using bcrypt.
    Returns a secure salt-hashed password string for DB storage.

    Args:
        plain_password (str): The plaintext password string.

    Returns:
        str: Salted bcrypt password hash string.
    """
    logger.info("Executing security.hash_password")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password string against a bcrypt hashed password.
    Returns True if the password matches, False otherwise.

    Args:
        plain_password (str): Plaintext password attempt.
        hashed_password (str): Stored bcrypt password hash string.

    Returns:
        bool: True if password matches, False otherwise.
    """
    logger.info("Executing security.verify_password")
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as error:
        logger.error(f"Error in security.verify_password: {error}")
        return False


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token containing subject (user_id) and expiration.
    Encodes token using configured JWT secret and algorithm.

    Args:
        subject (str): The user identifier to encode in token sub claim.
        expires_delta (Optional[timedelta]): Custom token validity duration.

    Returns:
        str: Encoded JWT bearer access token string.
    """
    logger.info(f"Executing security.create_access_token for subject {subject}")
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token string.
    Raises PyJWT exceptions if signature is invalid or token has expired.

    Args:
        token (str): The JWT bearer access token string.

    Returns:
        Dict[str, Any]: Decoded token claims dictionary containing sub.
    """
    logger.info("Executing security.decode_access_token")
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload
