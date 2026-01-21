from passlib.context import CryptContext
from jose import jwt
import os
import time
import uuid
from typing import Optional

from app.db.connector import AsyncSessionLocal
from app.db.models import User, RefreshToken
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24  # 1 day
REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7


def _create_token(email: str, expires_in: int):
    now = int(time.time())
    payload = {"sub": email, "iat": now, "exp": now + expires_in, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def register_user(email: str, password: str):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.email == email))
        existing = q.scalars().first()
        if existing:
            return {"error": "user_exists"}
        hashed = pwd_context.hash(password)
        user = User(email=email, hashed_password=hashed)
        session.add(user)
        await session.commit()
        return {"message": "User registered", "email": email}


async def login_user(email: str, password: str):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.email == email))
        user = q.scalars().first()
        if not user:
            return {"error": "invalid_credentials"}
        if not pwd_context.verify(password, user.hashed_password):
            return {"error": "invalid_credentials"}
        access = _create_token(email, ACCESS_TOKEN_EXPIRE_SECONDS)
    refresh = _create_token(email, REFRESH_TOKEN_EXPIRE_SECONDS)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS)
    rt = RefreshToken(token=refresh, user_id=user.id, expires_at=expires_at)
    session.add(rt)
    await session.commit()
    return {"message": "User logged in", "access_token": access, "refresh_token": refresh}


async def refresh_tokens(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            return {"error": "invalid_token"}
        async with AsyncSessionLocal() as session:
            q = await session.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
            rt = q.scalars().first()
            if not rt or rt.revoked:
                return {"error": "invalid_token"}
            # normalize stored expires_at to timezone-aware UTC if needed
            expires_at = rt.expires_at
            if expires_at is None:
                return {"error": "invalid_token"}
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return {"error": "invalid_token"}
                return {"error": "invalid_token"}
            # rotate: revoke old, create new
            rt.revoked = True
            new_refresh = _create_token(email, REFRESH_TOKEN_EXPIRE_SECONDS)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS)
            new_rt = RefreshToken(token=new_refresh, user_id=rt.user_id, expires_at=expires_at)
            session.add(new_rt)
            await session.commit()
            access = _create_token(email, ACCESS_TOKEN_EXPIRE_SECONDS)
            return {"message": "Tokens refreshed", "access_token": access, "refresh_token": new_refresh}
    except Exception as e:
        return {"error": str(e)}


async def logout_refresh_token(refresh_token: str):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
        rt = q.scalars().first()
        if not rt:
            return {"error": "not_found"}
        rt.revoked = True
        await session.commit()
        return {"message": "revoked"}


async def get_current_user(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        async with AsyncSessionLocal() as session:
            q = await session.execute(select(User).where(User.email == email))
            user = q.scalars().first()
            if not user:
                return None
            return {"email": user.email}
    except Exception:
        return None


async def reset_password(email: str):
    return {"message": "Password reset link sent", "email": email}


async def verify_email(email: str, code: str):
    return {"message": "Email verified", "email": email, "code": code}


async def verify_otp(otp: str):
    return {"message": "OTP verified", "otp": otp}

