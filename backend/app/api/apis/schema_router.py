"""Schema management routes.

Mounted on the APIs router at:
    POST   /apis/{api_id}/schemas
    GET    /apis/{api_id}/schemas
    GET    /apis/{api_id}/schemas/{schema_id}
    PUT    /apis/{api_id}/schemas/{schema_id}
    DELETE /apis/{api_id}/schemas/{schema_id}

Each API can have one or more schemas attached.  The gateway uses the
**first** schema (lowest id) to validate the request body before proxying.

Schema storage
--------------
- ``definition`` (JSON) — a JSON Schema object, e.g.
    {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
- ``raw`` (text) — optional raw/original schema text (kept for display only,
    not used for validation)

When ``definition`` is null the gateway skips validation for that schema row.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorizers.rbac import require_permission
from app.db.connector import get_db
from app.db.models import API, Schema
from app.logging_config import get_logger

logger = get_logger("api.schema_router")

router = APIRouter(tags=["schemas"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SchemaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    definition: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema object used for request body validation",
    )
    raw: Optional[str] = Field(
        None,
        description="Optional raw/original schema text (display only)",
    )


class SchemaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    definition: Optional[Dict[str, Any]] = None
    raw: Optional[str] = None


class SchemaOut(BaseModel):
    id: int
    api_id: int
    name: str
    definition: Optional[Dict[str, Any]] = None
    raw: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, s: Schema) -> "SchemaOut":
        return cls(
            id=s.id,
            api_id=s.api_id,
            name=s.name,
            definition=s.definition,
            raw=s.raw,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_api_or_404(api_id: int, db: AsyncSession) -> API:
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API {api_id} not found",
        )
    return api


async def _get_schema_or_404(api_id: int, schema_id: int, db: AsyncSession) -> Schema:
    result = await db.execute(
        select(Schema).where(
            Schema.id == schema_id,
            Schema.api_id == api_id,
        )
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found for API {api_id}",
        )
    return schema


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/{api_id}/schemas",
    response_model=SchemaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a schema to an API",
)
async def create_schema(
    api_id: int,
    payload: SchemaCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> SchemaOut:
    """Create and attach a JSON Schema to an API for request body validation.

    The gateway uses the **first** schema (by id) to validate inbound request
    bodies for methods that carry a body (POST, PUT, PATCH).  Requests that
    fail validation receive a **422** response with validation details before
    any upstream call is made.

    Set ``definition`` to ``null`` to register a schema record without
    activating validation (useful as a placeholder).
    """
    await _get_api_or_404(api_id, db)

    schema = Schema(
        api_id=api_id,
        name=payload.name,
        definition=payload.definition,
        raw=payload.raw,
    )
    db.add(schema)
    await db.commit()
    await db.refresh(schema)
    logger.info("Created schema id=%s for api_id=%s", schema.id, api_id)
    return SchemaOut.from_orm_obj(schema)


@router.get(
    "/{api_id}/schemas",
    response_model=List[SchemaOut],
    summary="List schemas attached to an API",
)
async def list_schemas(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> List[SchemaOut]:
    """Return all schemas attached to the given API, ordered by id."""
    await _get_api_or_404(api_id, db)
    result = await db.execute(
        select(Schema).where(Schema.api_id == api_id).order_by(Schema.id)
    )
    schemas = result.scalars().all()
    return [SchemaOut.from_orm_obj(s) for s in schemas]


@router.get(
    "/{api_id}/schemas/{schema_id}",
    response_model=SchemaOut,
    summary="Get a specific schema",
)
async def get_schema(
    api_id: int,
    schema_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> SchemaOut:
    """Retrieve a single schema by id."""
    schema = await _get_schema_or_404(api_id, schema_id, db)
    return SchemaOut.from_orm_obj(schema)


@router.put(
    "/{api_id}/schemas/{schema_id}",
    response_model=SchemaOut,
    summary="Update a schema",
)
async def update_schema(
    api_id: int,
    schema_id: int,
    payload: SchemaUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> SchemaOut:
    """Update a schema's name, JSON Schema definition, or raw text.

    Only fields present in the payload are updated (partial update).
    """
    schema = await _get_schema_or_404(api_id, schema_id, db)
    if payload.name is not None:
        schema.name = payload.name
    if payload.definition is not None:
        schema.definition = payload.definition
    if payload.raw is not None:
        schema.raw = payload.raw
    await db.commit()
    await db.refresh(schema)
    logger.info("Updated schema id=%s for api_id=%s", schema_id, api_id)
    return SchemaOut.from_orm_obj(schema)


@router.delete(
    "/{api_id}/schemas/{schema_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a schema",
)
async def delete_schema(
    api_id: int,
    schema_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> None:
    """Permanently delete a schema from an API.

    If this was the only schema, the gateway will stop validating request
    bodies for the API.
    """
    schema = await _get_schema_or_404(api_id, schema_id, db)
    await db.delete(schema)
    await db.commit()
    logger.info("Deleted schema id=%s for api_id=%s", schema_id, api_id)
