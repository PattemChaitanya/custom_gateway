"""CRUD operations for API deployments."""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import API, APIDeployment, Environment
from app.logging_config import get_logger

logger = get_logger("gateway.deployment_crud")

_VALID_STATUSES = {"draft", "active", "deprecated"}


async def get_deployment(
    db: AsyncSession, api_id: int, deployment_id: int
) -> Optional[APIDeployment]:
    result = await db.execute(
        select(APIDeployment)
        .options(selectinload(APIDeployment.environment))
        .where(APIDeployment.id == deployment_id, APIDeployment.api_id == api_id)
    )
    return result.scalar_one_or_none()


async def list_deployments(db: AsyncSession, api_id: int) -> List[APIDeployment]:
    result = await db.execute(
        select(APIDeployment)
        .options(selectinload(APIDeployment.environment))
        .where(APIDeployment.api_id == api_id)
        .order_by(APIDeployment.deployed_at.desc())
    )
    return list(result.scalars().all())


async def deploy_api(
    db: AsyncSession,
    api_id: int,
    environment_id: int,
    target_url_override: Optional[str],
    deployed_by: Optional[int],
    notes: Optional[str],
) -> APIDeployment:
    """Create or update the deployment of *api_id* to *environment_id*.

    - Verifies the API and Environment exist.
    - Upserts the ``APIDeployment`` row (one per api+env pair).
    - Promotes the API's lifecycle status to ``active`` if currently ``draft``.
    - Returns the upserted deployment (with ``environment`` eagerly loaded).
    """
    # Verify API exists
    api_result = await db.execute(select(API).where(API.id == api_id))
    api = api_result.scalar_one_or_none()
    if api is None:
        raise ValueError(f"API with id={api_id} not found")

    # Verify Environment exists
    env_result = await db.execute(
        select(Environment).where(Environment.id == environment_id)
    )
    env = env_result.scalar_one_or_none()
    if env is None:
        raise ValueError(f"Environment with id={environment_id} not found")

    # Upsert: check for existing deployment for this api+env pair
    existing_result = await db.execute(
        select(APIDeployment).where(
            APIDeployment.api_id == api_id,
            APIDeployment.environment_id == environment_id,
        )
    )
    deployment = existing_result.scalar_one_or_none()

    if deployment:
        # Re-activate if it was previously taken offline
        deployment.status = "deployed"
        deployment.target_url_override = target_url_override
        if deployed_by is not None:
            deployment.deployed_by = deployed_by
        if notes is not None:
            deployment.notes = notes
    else:
        deployment = APIDeployment(
            api_id=api_id,
            environment_id=environment_id,
            status="deployed",
            target_url_override=target_url_override,
            deployed_by=deployed_by,
            notes=notes,
        )
        db.add(deployment)

    # Promote API status from draft → active on first deployment
    if api.status == "draft":
        api.status = "active"

    await db.commit()
    await db.refresh(deployment)

    # Reload with environment relationship
    result = await db.execute(
        select(APIDeployment)
        .options(selectinload(APIDeployment.environment))
        .where(APIDeployment.id == deployment.id)
    )
    return result.scalar_one()


async def undeploy_api(
    db: AsyncSession, api_id: int, deployment_id: int
) -> Optional[APIDeployment]:
    """Mark a deployment as ``inactive`` (soft-delete).

    If the API has no remaining ``deployed`` deployments, its status is set
    back to ``draft``.
    """
    deployment = await get_deployment(db, api_id, deployment_id)
    if deployment is None:
        return None

    deployment.status = "inactive"
    await db.flush()

    # Check if any other active deployments remain; if not revert API to draft
    remaining = await db.execute(
        select(APIDeployment).where(
            APIDeployment.api_id == api_id,
            APIDeployment.status == "deployed",
        )
    )
    if not remaining.scalars().first():
        api_result = await db.execute(select(API).where(API.id == api_id))
        api = api_result.scalar_one_or_none()
        if api and api.status == "active":
            api.status = "draft"

    await db.commit()
    await db.refresh(deployment)
    return deployment


async def update_api_status(
    db: AsyncSession, api_id: int, new_status: str
) -> Optional[API]:
    """Manually set the API lifecycle status."""
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    if api is None:
        return None
    api.status = new_status
    await db.commit()
    await db.refresh(api)
    return api


async def find_deployment_for_env(
    db: AsyncSession, api_id: int, env_slug: str
) -> Optional[APIDeployment]:
    """Return the active deployment for an API in the named environment."""
    result = await db.execute(
        select(APIDeployment)
        .join(APIDeployment.environment)
        .options(selectinload(APIDeployment.environment))
        .where(
            APIDeployment.api_id == api_id,
            APIDeployment.status == "deployed",
            Environment.slug == env_slug,
        )
    )
    return result.scalar_one_or_none()
