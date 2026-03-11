from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
from typing import List

from ...db.connector import get_db
from . import schemas
from . import crud
from .deployment_router import router as deployment_router
from .rate_limit_router import router as rate_limit_router
from .auth_policy_router import router as auth_policy_router
from .schema_router import router as schema_router
from .lb_router import router as lb_router
from app.authorizers.rbac import require_permission
from app.db.models import User


router = APIRouter(prefix="/apis", tags=["apis"])

# Mount deployment sub-routes: /apis/{id}/deployments, /apis/{id}/status
router.include_router(deployment_router)
# Mount rate-limit sub-routes: /apis/{id}/rate-limits
router.include_router(rate_limit_router)
# Mount auth-policy sub-routes: /apis/{id}/auth-policies
router.include_router(auth_policy_router)
# Mount schema sub-routes: /apis/{id}/schemas
router.include_router(schema_router)
# Mount backend-pool sub-routes: /apis/{id}/backend-pools
router.include_router(lb_router)


@router.post("/", response_model=schemas.APIMeta, status_code=status.HTTP_201_CREATED)
async def create_api(
    payload: schemas.CreateAPIRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("api:create")),
):
    try:
        api = await crud.create_api(db, payload.model_dump())
        return api
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=List[schemas.APIMeta])
async def list_apis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("api:list")),
):
    return await crud.list_apis(db)


@router.get("/{api_id}", response_model=schemas.APIMeta)
async def get_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("api:read")),
):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    return api


@router.put("/{api_id}", response_model=schemas.APIMeta)
async def update_api(
    api_id: int,
    payload: schemas.UpdateAPIRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("api:update")),
):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    patch = payload.model_dump(exclude_none=True)
    api = await crud.update_api(db, api, patch)
    return api


@router.delete("/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("api:delete")),
):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    await crud.delete_api(db, api)
    return None
