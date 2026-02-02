"""
Compatibility shim for API schemas. The canonical API schemas now live in
`app.api.apis.schemas`. Importing from here forwards to that module.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from .apis.schemas import *  # noqa: F401,F403



class SchemaModel(BaseModel):
    id: int | None = None
    api_id: int
    name: str
    definition: Optional[Dict[str, Any]] | None = None
    raw: Optional[str] | None = None

    class Config:
        orm_mode = True


class AuthPolicyModel(BaseModel):
    id: int | None = None
    api_id: int
    name: str
    type: str
    config: Optional[Dict[str, Any]] | None = None

    class Config:
        orm_mode = True


class RateLimitModel(BaseModel):
    id: int | None = None
    api_id: int
    name: str
    key_type: str
    limit: int
    window_seconds: int

    class Config:
        orm_mode = True


class ConnectorModel(BaseModel):
    id: int | None = None
    api_id: Optional[int] | None = None
    name: str
    type: str
    config: Optional[Dict[str, Any]] | None = None

    class Config:
        orm_mode = True


class EnvironmentModel(BaseModel):
    id: int | None = None
    name: str
    slug: str
    description: Optional[str] | None = None

    class Config:
        orm_mode = True


class APIKeyModel(BaseModel):
    id: int | None = None
    key: str
    label: Optional[str] | None= None
    scopes: Optional[str] | None = None
    revoked: Optional[bool] | None = False
    environment_id: Optional[int] | None = None

    class Config:
        orm_mode = True


class ModuleMetadataModel(BaseModel):
    id: int | None = None
    name: str
    version: Optional[str] | None = None
    description: Optional[str] | None = None
    metadata: Optional[Dict[str, Any]] | None = None

    class Config:
        orm_mode = True
