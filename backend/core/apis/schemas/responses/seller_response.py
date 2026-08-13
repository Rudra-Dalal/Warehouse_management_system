from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SellerResponse(BaseModel):
    """Response schema exposing public seller profile metadata.
    Contains seller code, business name, contact info, and timestamps.
    """

    id: str = Field(..., description="Seller ObjectId string")
    code: str = Field(..., description="Unique seller code string")
    name: str = Field(..., description="Seller business name")
    email: Optional[str] = Field(default=None, description="Contact email address")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    is_active: bool = Field(..., description="Active seller status flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
