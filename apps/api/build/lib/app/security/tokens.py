import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import get_settings
def create_access_token(subject: str) -> str:
    settings = get_settings(); expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return jwt.encode({"sub": subject, "type": "access", "exp": expiry}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
def create_opaque_token() -> str: return secrets.token_urlsafe(48)
def hash_token(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
