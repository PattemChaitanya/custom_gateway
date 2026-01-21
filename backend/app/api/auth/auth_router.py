from fastapi import APIRouter, Body, Depends
from .auth_service import (
    login_user,
    reset_password,
    refresh_tokens,
    register_user,
    verify_email,
    verify_otp,
    get_current_user,
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

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/")
async def root_info():
    return {"Auth": "This is the Auth endpoint"}

@router.get("/me")
async def get_me(current_user: dict = Depends(_get_current_user_dep)):
    # current_user is provided by dependency which validates the Authorization header
    return {"message": "Current user", "email": current_user.get("email")}

@router.post("/login")
async def login_route(payload: UserLogin):
    return await login_user(payload.email, payload.password)

@router.post("/reset-password")
async def reset_password_route(payload: PasswordReset):
    return await reset_password(payload.email)

@router.post("/refresh-tokens")
async def refresh_tokens_route(payload: TokenRefresh):
    return await refresh_tokens(payload.refresh_token)

@router.post("/logout")
async def logout(payload: TokenRefresh):
    # revoke refresh token
    result = await logout_refresh_token(payload.refresh_token)
    # keep response simple
    return {"message": "User logged out"}

@router.post("/register")
async def register_route(payload: UserRegister):
    return await register_user(payload.email, payload.password)

@router.post("/verify-email")
async def verify_email_route(payload: EmailVerification):
    return await verify_email(payload.email, payload.code)

@router.post("/verify-otp")
async def verify_otp_route(payload: OTPVerification):
    return await verify_otp(payload.otp)

