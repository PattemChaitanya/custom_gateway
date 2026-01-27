from pydantic import BaseModel
from typing import Any, Dict, Optional


class APIMeta(BaseModel):
    id: Optional[int]
    name: str
    version: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

    # Pydantic v2 configuration to allow creating models from ORM objects
    model_config = {"from_attributes": True}


class CreateAPIRequest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class UpdateAPIRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

