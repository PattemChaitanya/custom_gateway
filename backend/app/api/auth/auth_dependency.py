from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from .auth_service import get_current_user as _get_current_user_service
from app.db.connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), session: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return _checker
