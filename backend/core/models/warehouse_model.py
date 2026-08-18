from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class WarehouseModel(BaseModel):
    """Domain model representing a physical warehouse location.
    Used for inventory segregation, operational scoping, and RBAC authorization.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    code: str = Field(..., description="Unique alphanumeric warehouse code (e.g., RENO, COLUMBUS)")
    name: str = Field(..., description="Human-readable warehouse name")
    city: str = Field(default="", description="City location")
    state: str = Field(default="", description="State location")
    is_active: bool = Field(default=True, description="Active operational status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
