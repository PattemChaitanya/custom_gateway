from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class APIMeta(BaseModel):
    id: Optional[int]
    name: str
    version: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    type: Optional[str] = None
    resource: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    # Pydantic v2 configuration to allow creating models from ORM objects
    model_config = {"from_attributes": True}


class CreateAPIRequest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    type: Optional[str] = None
    resource: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")


class UpdateAPIRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    type: Optional[str] = None
    resource: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

