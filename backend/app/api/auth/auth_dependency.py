from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from .auth_service import get_current_user as _get_current_user_service
from app.db.connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Keep HTTPBearer but allow cookie fallback for access token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
):
    # Prefer Authorization header if present
    token = None
    if credentials and getattr(credentials, 'credentials', None):
        token = credentials.credentials
    # Fallback to cookie named 'access_token' (for HttpOnly cookie flows)
    if not token:
        token = request.cookies.get('access_token')

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    try:
        user = await _get_current_user_service(token, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials"
            )
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )


def require_role(role: str):
    """Dependency factory that returns a dependency which enforces the given role.

    - Accepts a single role string (case-sensitive match against comma-separated roles on the user)
    - Superusers bypass role checks
    """

    async def _checker(current_user: dict = Depends(get_current_user)):
        # current_user has keys: email, roles (comma-separated), is_superuser
        if current_user.get('is_superuser'):
            return current_user
        roles_claim = current_user.get('roles') or ''
        user_roles = [r.strip() for r in roles_claim.split(',') if r.strip()]
        if role in user_roles:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Insufficient permissions")

    return _checker
