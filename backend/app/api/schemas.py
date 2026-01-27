"""
Compatibility shim for API schemas. The canonical API schemas now live in
`app.api.apis.schemas`. Importing from here forwards to that module.
"""

from .apis.schemas import *  # noqa: F401,F403



class SchemaModel(BaseModel):
    id: Optional[int]
    api_id: int
    name: str
    definition: Optional[Dict[str, Any]] = None
    raw: Optional[str] = None

    class Config:
        orm_mode = True


class AuthPolicyModel(BaseModel):
    id: Optional[int]
    api_id: int
    name: str
    type: str
    config: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class RateLimitModel(BaseModel):
    id: Optional[int]
    api_id: int
    name: str
    key_type: str
    limit: int
    window_seconds: int

    class Config:
        orm_mode = True


class ConnectorModel(BaseModel):
    id: Optional[int]
    api_id: Optional[int]
    name: str
    type: str
    config: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class EnvironmentModel(BaseModel):
    id: Optional[int]
    name: str
    slug: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class APIKeyModel(BaseModel):
    id: Optional[int]
    key: str
    label: Optional[str] = None
    scopes: Optional[str] = None
    revoked: Optional[bool] = False
    environment_id: Optional[int] = None

    class Config:
        orm_mode = True


class ModuleMetadataModel(BaseModel):
    id: Optional[int]
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
