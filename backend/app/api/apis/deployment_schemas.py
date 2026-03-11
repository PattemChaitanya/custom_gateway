"""Pydantic schemas for API deployment resources."""

from typing import Optional
from pydantic import BaseModel, Field


class DeployRequest(BaseModel):
    """Request body for deploying an API to an environment."""
    environment_id: int = Field(...,
                                description="ID of the target Environment")
    target_url_override: Optional[str] = Field(
        None,
        description=(
            "Per-environment upstream URL. Overrides api.config.target_url "
            "for this stage. Leave null to inherit the API's global target."
        ),
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Free-text deployment notes"
    )


class DeploymentOut(BaseModel):
    """Serialised APIDeployment record returned to the client."""
    id: int
    api_id: int
    environment_id: int
    environment_slug: Optional[str] = None
    environment_name: Optional[str] = None
    status: str
    target_url_override: Optional[str] = None
    deployed_by: Optional[int] = None
    deployed_at: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class APIStatusUpdate(BaseModel):
    """Request body for manually changing an API's lifecycle status."""
    status: str = Field(
        ...,
        pattern="^(draft|active|deprecated)$",
        description="New status: draft | active | deprecated",
    )
