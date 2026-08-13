from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class RoleModel(BaseModel):
    """Domain model representing a security role entity.
    Groups system permissions and assigns capability sets to users.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., description="Unique security role name identifier")
    description: str = Field(default="", description="Role responsibilities description")
    permission_ids: List[str] = Field(default_factory=list, description="List of assigned Permission ObjectIds")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
