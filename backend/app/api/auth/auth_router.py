from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import JSONResponse
import os

# cookie security settings (configurable via env)
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() in ("1", "true", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")  # 'lax'|'strict'|'none'
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

def set_refresh_cookie(response: Response, token: str):
    # when SameSite=None, Secure must be True in modern browsers
    samesite = COOKIE_SAMESITE if COOKIE_SAMESITE in ("lax", "strict", "none") else "lax"
    secure = SECURE_COOKIES
    if samesite == "none":
        # ensure secure when None
        secure = True
    # set cookie
    response.set_cookie(
        "refresh_token",
        token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
        domain=COOKIE_DOMAIN,
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie("refresh_token", path="/", domain=COOKIE_DOMAIN)
from .auth_service import (
    login_user,
    reset_password,
    refresh_tokens,
    register_user,
    verify_email,
    verify_otp,
    logout_refresh_token,
)
from .auth_schema import (
    UserLogin,
    UserRegister,
    PasswordReset,
    TokenRefresh,
    EmailVerification,
    OTPVerification,
)
from .auth_dependency import get_current_user as _get_current_user_dep
from app.db.connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/")
async def root_info():
    return {"Auth": "This is the Auth endpoint"}

@router.get("/me")
async def get_me(current_user: dict = Depends(_get_current_user_dep)):
    # current_user is provided by dependency which validates the Authorization header
    return {"message": "Current user", "email": current_user.get("email")}

@router.post("/login")
async def login_route(payload: UserLogin, response: Response, session: AsyncSession = Depends(get_db)):
    # login_user returns {'access_token': ..., 'refresh_token': ...}
    data = await login_user(payload.email, payload.password, session)
    # if login failed, return directly
    if data.get("error"):
        return data
    # set refresh token as HttpOnly cookie and return access token in body
    refresh = data.get("refresh_token")
    if refresh:
        set_refresh_cookie(response, refresh)
    return {"message": data.get("message"), "access_token": data.get("access_token")}

@router.post("/reset-password")
async def reset_password_route(payload: PasswordReset, session: AsyncSession = Depends(get_db)):
    return await reset_password(payload.email)

@router.post("/refresh-tokens")
async def refresh_tokens_route(
    request: Request, payload: TokenRefresh | None = None, session: AsyncSession = Depends(get_db)
):
    # prefer cookie if present (HttpOnly cookie set by login), otherwise fall back to payload
    refresh_token = None
    if payload and getattr(payload, "refresh_token", None):
        refresh_token = payload.refresh_token
    else:
        refresh_token = request.cookies.get("refresh_token")

    result = await refresh_tokens(refresh_token, session)
    # if refresh returned a new refresh token, set it as cookie
    if result.get("refresh_token"):
        content = {k: v for k, v in result.items() if k != "refresh_token"}
        resp = JSONResponse(content=content)
        set_refresh_cookie(resp, result["refresh_token"])
        return resp
    return result

@router.post("/logout")
async def logout(payload: TokenRefresh | None = None, request: Request = None, response: Response = None, session: AsyncSession = Depends(get_db)):
    # support body-provided refresh_token or cookie
    refresh_token = None
    if payload and getattr(payload, "refresh_token", None):
        refresh_token = payload.refresh_token
    elif request:
        refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        await logout_refresh_token(refresh_token, session)

    # clear cookie
    if response:
        clear_refresh_cookie(response)
    return {"message": "User logged out"}

@router.post("/register")
async def register_route(payload: UserRegister, session: AsyncSession = Depends(get_db)):
    return await register_user(payload.email, payload.password, session)

@router.post("/verify-email")
async def verify_email_route(payload: EmailVerification, session: AsyncSession = Depends(get_db)):
    return await verify_email(payload.email, payload.code)

@router.post("/verify-otp")
async def verify_otp_route(payload: OTPVerification, session: AsyncSession = Depends(get_db)):
    return await verify_otp(payload.otp)

