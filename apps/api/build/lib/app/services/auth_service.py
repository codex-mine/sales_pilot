from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.entities import RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, create_opaque_token, hash_token
class AuthService:
    def __init__(self, db: AsyncSession): self.db = db
    async def register(self, payload: RegisterRequest) -> User:
        if await self.db.scalar(select(User).where(User.email == str(payload.email).lower())): raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        user = User(email=str(payload.email).lower(), password_hash=hash_password(payload.password), full_name=payload.full_name)
        self.db.add(user); await self.db.commit(); await self.db.refresh(user); return user
    async def authenticate(self, payload: LoginRequest) -> User:
        user = await self.db.scalar(select(User).where(User.email == str(payload.email).lower()))
        if not user or not verify_password(payload.password, user.password_hash): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
        return user
    async def issue_tokens(self, user: User) -> tuple[str, str]:
        raw_refresh = create_opaque_token(); expiry = datetime.now(timezone.utc) + timedelta(days=get_settings().jwt_refresh_token_expire_days)
        self.db.add(RefreshToken(user_id=user.id, token_hash=hash_token(raw_refresh), expires_at=expiry)); await self.db.commit()
        return create_access_token(str(user.id)), raw_refresh
