from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class SellerModel(BaseModel):
    """Domain model representing an e-commerce seller whose inventory Whitfield fulfills.
    Identified by a unique seller code and contact profile information.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    code: str = Field(..., description="Unique seller business code identifier")
    name: str = Field(..., description="Full seller business name")
    email: Optional[str] = Field(default=None, description="Contact email address")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    is_active: bool = Field(default=True, description="Active seller status flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
