"""
Application-level encryption for third-party credentials stored at rest
(Integration.access_token_encrypted — AI provider API keys, and later OAuth
tokens). The Integration model's docstring mandates application-level
encryption, not DB-level; this module is the single implementation of it.

Fernet (AES-128-CBC + HMAC, via `cryptography`) is used because it is
authenticated, versioned, and ships with the `cryptography` package already
present transitively through `python-jose[cryptography]` (declared explicitly
in pyproject so the dependency is not accidental).
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.exceptions.errors import ValidationError


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    if settings.credentials_encryption_key:
        key = settings.credentials_encryption_key.encode()
    else:
        # Development fallback: derive a stable Fernet key from the JWT
        # secret. Production deployments should set CREDENTIALS_ENCRYPTION_KEY
        # so rotating the JWT secret doesn't orphan stored credentials.
        digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValidationError(
            "Stored credential cannot be decrypted — it was encrypted with a "
            "different CREDENTIALS_ENCRYPTION_KEY. Re-enter the API key."
        ) from exc
