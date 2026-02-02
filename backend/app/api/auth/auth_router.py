from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import JSONResponse
import os

from .auth_service import (
    login_user,
    reset_password,
    generate_otp,
    generate_email_code,
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
    SendCode,
)
from .auth_dependency import get_current_user as _get_current_user_dep, require_role
# from .auth_dependency import 
from .auth_service import get_user_roles, set_user_roles
from .auth_service import list_users
from app.db.connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession

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


router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/")
async def root_info():
    return {"Auth": "This is the Auth endpoint"}

@router.get("/me")
async def get_me(current_user: dict = Depends(_get_current_user_dep)):
    # current_user is provided by dependency which validates the Authorization header
    return {"message": "Current user", "email": current_user.get("email")}


@router.get("/admin-area")
async def admin_area(current_user: dict = Depends(require_role('admin'))):
    # example protected endpoint requiring 'admin' role (superusers bypass checks)
    return {"message": "Welcome to admin area", "email": current_user.get("email")}

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
    # return both tokens in JSON for test clients; cookie still set for browsers
    return {"message": data.get("message"), "access_token": data.get("access_token"), "refresh_token": refresh}

@router.post("/reset-password")
async def reset_password_route(payload: PasswordReset, session: AsyncSession = Depends(get_db)):
    return await reset_password(payload.email)


@router.post("/send-otp")
async def send_otp_route(payload: SendCode, session: AsyncSession = Depends(get_db)):
    # backward-compatible wrapper that delegates to the unified send handler
    # prefer mobile if provided, otherwise use email
    return await send_code_route(payload, transport='otp', session=session)


@router.post("/send-email-code")
async def send_email_code_route(payload: SendCode, session: AsyncSession = Depends(get_db)):
    # backward-compatible wrapper that delegates to the unified send handler
    return await send_code_route(payload, transport='email', session=session)


@router.post("/resend-otp")
async def resend_otp_route(payload: SendCode, session: AsyncSession = Depends(get_db)):
    # resend is the same as send in our unified handler (cooldown handled by service)
    return await send_code_route(payload, transport='otp', session=session)


@router.post("/send-code")
async def send_code_route(payload: SendCode, transport: str = 'otp', session: AsyncSession = Depends(get_db)):
    """Unified endpoint for sending or resending verification codes.

    - transport: 'otp' (default) or 'email'
    - cooldown / resend limits are enforced by the service layer; this endpoint simply delegates.
    """
    t = (transport or 'otp').lower()
    # mobile verification uses the 'mobile' field in payload; map transport 'otp' to mobile if provided
    if t == 'email':
        if not payload.email:
            return {"error": "missing_email"}
        return await generate_email_code(payload.email, session)

    # otp / mobile transport
    target = payload.mobile if payload.mobile else payload.email
    if not target:
        return {"error": "missing_target"}
    # service functions were designed around email, but accept a string identifier — pass mobile when used
    return await generate_otp(target, session)

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


@router.get("/users/{email}/roles")
async def get_roles_route(email: str, current_user: dict = Depends(require_role('admin')), session: AsyncSession = Depends(get_db)):
    roles = await get_user_roles(email, session)
    if roles is None:
        return {"error": "not_found"}
    return {"email": email, "roles": roles}


@router.post("/users/{email}/roles")
async def set_roles_route(email: str, payload: dict, current_user: dict = Depends(require_role('admin')), session: AsyncSession = Depends(get_db)):
    # payload should contain 'roles' string, e.g. 'admin,editor'
    roles = payload.get('roles')
    if roles is None:
        return {"error": "missing_roles"}
    return await set_user_roles(email, roles, session)

@router.post("/verify-email")
async def verify_email_route(payload: EmailVerification, session: AsyncSession = Depends(get_db)):
    return await verify_email(payload.email, payload.code, session)

@router.post("/verify-otp")
async def verify_otp_route(payload: OTPVerification, session: AsyncSession = Depends(get_db)):
    # payload.otp currently doesn't include the email so verification requires email in real flows
    # for tests where otp is global, caller may use the test default '9999'
    # If clients provide email as well, consider adding a dedicated schema.
    # Here we attempt to verify by scanning recent entries (legacy behavior retained via service fallback)
    # Prefer passing email explicitly; for now call verify_otp with empty email to allow test OTP
    return await verify_otp(payload.email, payload.otp, session)


@router.get("/users")
async def get_users_route(current_user: dict = Depends(require_role('admin')), session: AsyncSession = Depends(get_db)):
    """Admin-only endpoint that returns a list of users with basic fields."""
    return await list_users(session)

