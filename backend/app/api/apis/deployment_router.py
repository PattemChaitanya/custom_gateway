"""Deployment management routes.

Mounted on the APIs router at:
    POST   /apis/{api_id}/deployments
    GET    /apis/{api_id}/deployments
    GET    /apis/{api_id}/deployments/{deployment_id}
    DELETE /apis/{api_id}/deployments/{deployment_id}
    PATCH  /apis/{api_id}/status
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connector import get_db
from app.logging_config import get_logger
from app.authorizers.rbac import require_permission

from .deployment_crud import (
    deploy_api,
    find_deployment_for_env,
    get_deployment,
    list_deployments,
    undeploy_api,
    update_api_status,
)
from .deployment_schemas import APIStatusUpdate, DeploymentOut, DeployRequest

logger = get_logger("gateway.deployment_router")

router = APIRouter(tags=["deployments"])


def _serialize(dep) -> DeploymentOut:
    env = dep.environment
    return DeploymentOut(
        id=dep.id,
        api_id=dep.api_id,
        environment_id=dep.environment_id,
        environment_slug=env.slug if env else None,
        environment_name=env.name if env else None,
        status=dep.status,
        target_url_override=dep.target_url_override,
        deployed_by=dep.deployed_by,
        deployed_at=dep.deployed_at.isoformat() if dep.deployed_at else None,
        notes=dep.notes,
    )


@router.post(
    "/{api_id}/deployments",
    response_model=DeploymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy an API to an environment",
)
async def create_deployment(
    api_id: int,
    payload: DeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api:update")),
) -> DeploymentOut:
    """Deploy (or re-deploy) an API to a target environment.

    - Creates an ``APIDeployment`` record linking the API to the environment.
    - If ``target_url_override`` is provided, the gateway will use it instead
      of the API's global ``config.target_url`` for this environment.
    - Promotes the API's lifecycle status from ``draft`` → ``active`` on first
      successful deployment.

    Re-deploying an already-deployed API to the same environment is idempotent
    and updates the override URL + notes.
    """
    deployed_by: Optional[int] = getattr(current_user, "id", None)

    try:
        dep = await deploy_api(
            db,
            api_id=api_id,
            environment_id=payload.environment_id,
            target_url_override=payload.target_url_override,
            deployed_by=deployed_by,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    logger.info(
        "API %s deployed to environment %s by user=%s",
        api_id,
        payload.environment_id,
        deployed_by,
    )
    return _serialize(dep)


@router.get(
    "/{api_id}/deployments",
    response_model=List[DeploymentOut],
    summary="List all deployments for an API",
)
async def list_api_deployments(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> List[DeploymentOut]:
    deps = await list_deployments(db, api_id)
    return [_serialize(d) for d in deps]


@router.get(
    "/{api_id}/deployments/{deployment_id}",
    response_model=DeploymentOut,
    summary="Get a single deployment record",
)
async def get_api_deployment(
    api_id: int,
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> DeploymentOut:
    dep = await get_deployment(db, api_id, deployment_id)
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found for API {api_id}",
        )
    return _serialize(dep)


@router.delete(
    "/{api_id}/deployments/{deployment_id}",
    response_model=DeploymentOut,
    summary="Undeploy an API from an environment (soft-delete)",
)
async def delete_deployment(
    api_id: int,
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> DeploymentOut:
    """Mark a deployment as ``inactive``.

    The API is no longer reachable through the gateway for that environment.
    If it was the last active deployment, the API's lifecycle status reverts
    to ``draft``.
    """
    dep = await undeploy_api(db, api_id, deployment_id)
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found for API {api_id}",
        )
    logger.info("API %s deployment %s set to inactive", api_id, deployment_id)
    return _serialize(dep)


@router.patch(
    "/{api_id}/status",
    summary="Manually update an API's lifecycle status",
)
async def patch_api_status(
    api_id: int,
    payload: APIStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> dict:
    """Manually override the API lifecycle status.

    Valid values: ``draft`` | ``active`` | ``deprecated``

    Deprecating an API does **not** remove deployments — the gateway will
    return ``410 Gone`` for requests to a deprecated API.
    """
    api = await update_api_status(db, api_id, payload.status)
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API {api_id} not found",
        )
    return {"api_id": api_id, "status": api.status}
