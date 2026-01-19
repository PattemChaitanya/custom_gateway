from fastapi import APIRouter
from .auth_service import login_user, reset_password, refresh_tokens, register_user, verify_email, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/")
async def get_me():
    return {"Auth": "This is the Auth endpoint"}

@router.get("/me")
async def get_me():
    return {"user": "This is the current user"}

@router.post("/login")
async def login(user: dict, password: str):
    return login_user(user, password)

@router.post("/reset-password")
async def reset_password(email: str):
    return reset_password(email)

@router.post("/refresh-tokens")
async def refresh_tokens(token: str):
    return refresh_tokens(token)

@router.post("/logout")
async def logout():
    return {"message": "User logged out"}

@router.post("/register")
async def register(user: dict, password: str):
    return register_user(user, password)

@router.post("/verify-email")
async def verify_email(email: str, code: str):
    return verify_email(email, code)

@router.post("/verify-otp")
async def verify_otp(otp: str):
    return verify_otp(otp)

