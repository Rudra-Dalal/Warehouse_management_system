from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class PermissionModel(BaseModel):
    """Domain model representing a system permission entity.
    Defines granular access capabilities for Role-Based Access Control.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., description="Unique permission name identifier")
    description: str = Field(default="", description="Detailed description of permission capability")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
