"""Connectors management router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.db.connector import get_db
from app.connectors.manager import ConnectorManager
from app.api.auth.auth_dependency import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/connectors", tags=["Connectors"])


# Pydantic schemas
class ConnectorCreate(BaseModel):
    """Schema for creating a connector."""
    name: str = Field(..., min_length=1, max_length=255, description="Connector name")
    type: str = Field(..., description="Connector type (postgresql, mongodb, redis, kafka, s3, azure)")
    config: dict = Field(..., description="Connector configuration")
    api_id: Optional[int] = Field(None, description="Associated API ID")


class ConnectorUpdate(BaseModel):
    """Schema for updating a connector."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    config: Optional[dict] = None
    api_id: Optional[int] = None


class ConnectorResponse(BaseModel):
    """Schema for connector response."""
    id: int
    name: str
    type: str
    config: dict
    api_id: Optional[int]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class ConnectorTestResult(BaseModel):
    """Schema for connector test result."""
    connector_id: int
    status: str
    connected: bool
    error: Optional[str] = None


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(
    connector_data: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new connector.
    
    Requires authentication. Creates a connector configuration that can be used
    to connect to external services (databases, queues, storage).
    """
    manager = ConnectorManager(db)
    
    try:
        connector = await manager.create_connector(
            name=connector_data.name,
            connector_type=connector_data.type,
            config=connector_data.config,
            api_id=connector_data.api_id,
        )
        
        return ConnectorResponse(
            id=connector.id,
            name=connector.name,
            type=connector.type,
            config=connector.config,
            api_id=connector.api_id,
            created_at=connector.created_at.isoformat() if connector.created_at else "",
            updated_at=connector.updated_at.isoformat() if connector.updated_at else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connector: {str(e)}"
        )


@router.get("", response_model=List[ConnectorResponse])
async def list_connectors(
    api_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all connectors.
    
    Optionally filter by API ID.
    """
    manager = ConnectorManager(db)
    
    try:
        connectors = await manager.list_connectors(api_id=api_id)
        
        return [
            ConnectorResponse(
                id=c.id,
                name=c.name,
                type=c.type,
                config=c.config,
                api_id=c.api_id,
                created_at=c.created_at.isoformat() if c.created_at else "",
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
            )
            for c in connectors
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connectors: {str(e)}"
        )


@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific connector by ID."""
    manager = ConnectorManager(db)
    
    connector = await manager.get_connector(connector_id)
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    return ConnectorResponse(
        id=connector.id,
        name=connector.name,
        type=connector.type,
        config=connector.config,
        api_id=connector.api_id,
        created_at=connector.created_at.isoformat() if connector.created_at else "",
        updated_at=connector.updated_at.isoformat() if connector.updated_at else None,
    )


@router.put("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: int,
    connector_data: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a connector."""
    manager = ConnectorManager(db)
    
    # Build update dict
    update_data = {}
    if connector_data.name is not None:
        update_data["name"] = connector_data.name
    if connector_data.type is not None:
        update_data["type"] = connector_data.type
    if connector_data.config is not None:
        update_data["config"] = connector_data.config
    if connector_data.api_id is not None:
        update_data["api_id"] = connector_data.api_id
    
    connector = await manager.update_connector(connector_id, **update_data)
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    return ConnectorResponse(
        id=connector.id,
        name=connector.name,
        type=connector.type,
        config=connector.config,
        api_id=connector.api_id,
        created_at=connector.created_at.isoformat() if connector.created_at else "",
        updated_at=connector.updated_at.isoformat() if connector.updated_at else None,
    )


@router.delete("/{connector_id}", status_code=status.HTTP_200_OK)
async def delete_connector(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a connector."""
    manager = ConnectorManager(db)
    
    success = await manager.delete_connector(connector_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    return {"message": f"Connector {connector_id} deleted successfully"}


@router.post("/{connector_id}/test", response_model=ConnectorTestResult)
async def test_connector(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test connector connection.
    
    Attempts to connect to the external service and verify connectivity.
    """
    manager = ConnectorManager(db)
    
    try:
        result = await manager.test_connector(connector_id)
        return ConnectorTestResult(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connector: {str(e)}"
        )
