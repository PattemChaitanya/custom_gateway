"""
Gateway Routes router — CRUD for per-account proxy route definitions.

Every mutating operation (create / update / delete / toggle) fires a
POST {gateway_url}/internal/reload to hot-reload the live runtime.
Reload failures are logged as warnings but never block the response (T5.2).

Endpoints
---------
POST   /api/gateway-routes             — create route
GET    /api/gateway-routes             — list routes for caller's account
GET    /api/gateway-routes/{id}        — get single route
PUT    /api/gateway-routes/{id}        — full update
PATCH  /api/gateway-routes/{id}/toggle — flip active flag
DELETE /api/gateway-routes/{id}        — delete route
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.db.connector import get_db
from app.db.models import GatewayRoute
from app.gateway.reload import trigger_reload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gateway-routes", tags=["Gateway Routes"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RouteCreate(BaseModel):
    path: str = Field(..., min_length=1, description="Express-style path, e.g. /users/:id")
    method: str = Field(default="ANY", pattern=r"^(GET|POST|PUT|PATCH|DELETE|ANY)$")
    target_url: str = Field(..., min_length=1)
    auth_required: bool = False
    validation_schema: Optional[Dict[str, Any]] = None
    active: bool = True


class RouteUpdate(BaseModel):
    path: Optional[str] = None
    method: Optional[str] = Field(default=None, pattern=r"^(GET|POST|PUT|PATCH|DELETE|ANY)$")
    target_url: Optional[str] = None
    auth_required: Optional[bool] = None
    validation_schema: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class RouteResponse(BaseModel):
    id: int
    account_id: int
    path: str
    method: str
    target_url: str
    auth_required: bool
    validation_schema: Optional[Dict[str, Any]]
    active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    model_config = {"from_attributes": True}


def _to_response(r: GatewayRoute) -> RouteResponse:
    return RouteResponse(
        id=r.id,
        account_id=r.account_id,
        path=r.path,
        method=r.method,
        target_url=r.target_url,
        auth_required=r.auth_required,
        validation_schema=r.validation_schema,
        active=r.active,
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
    )


def _assert_owns(current_user: dict, route: GatewayRoute) -> None:
    if current_user.get("is_superuser"):
        return
    if current_user.get("account_id") == route.account_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Fire-and-forget reload (T5.1 + T5.2) ─────────────────────────────────────

def _fire_reload(account_id: int, db: AsyncSession) -> None:
    """Schedule reload as a background task — never blocks the response."""
    asyncio.create_task(trigger_reload(account_id, db))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a gateway route",
)
async def create_route(
    body: RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    account_id: Optional[int] = current_user.get("account_id")
    if not account_id and not current_user.get("is_superuser"):
        raise HTTPException(status_code=400, detail="No account associated with this user")

    route = GatewayRoute(
        account_id=account_id,
        path=body.path,
        method=body.method,
        target_url=body.target_url,
        auth_required=body.auth_required,
        validation_schema=body.validation_schema,
        active=body.active,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)

    _fire_reload(account_id, db)
    return _to_response(route)


@router.get(
    "",
    response_model=List[RouteResponse],
    summary="List gateway routes for the caller's account",
)
async def list_routes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    account_id: Optional[int] = current_user.get("account_id")
    stmt = select(GatewayRoute).order_by(GatewayRoute.id)
    if account_id and not current_user.get("is_superuser"):
        stmt = stmt.where(GatewayRoute.account_id == account_id)
    result = await db.execute(stmt)
    return [_to_response(r) for r in result.scalars().all()]


@router.get(
    "/{route_id}",
    response_model=RouteResponse,
    summary="Get a single gateway route",
)
async def get_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    route = await db.get(GatewayRoute, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    _assert_owns(current_user, route)
    return _to_response(route)


@router.put(
    "/{route_id}",
    response_model=RouteResponse,
    summary="Update a gateway route",
)
async def update_route(
    route_id: int,
    body: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    route = await db.get(GatewayRoute, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    _assert_owns(current_user, route)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(route, field, value)

    await db.commit()
    await db.refresh(route)

    _fire_reload(route.account_id, db)
    return _to_response(route)


@router.patch(
    "/{route_id}/toggle",
    response_model=RouteResponse,
    summary="Toggle a route's active flag",
)
async def toggle_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    route = await db.get(GatewayRoute, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    _assert_owns(current_user, route)

    route.active = not route.active
    await db.commit()
    await db.refresh(route)

    _fire_reload(route.account_id, db)
    return _to_response(route)


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a gateway route",
)
async def delete_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    route = await db.get(GatewayRoute, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    _assert_owns(current_user, route)

    account_id = route.account_id
    await db.delete(route)
    await db.commit()

    _fire_reload(account_id, db)
