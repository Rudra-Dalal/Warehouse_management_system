import enum
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class FulfillmentStatus(str, enum.Enum):
    """Controlled enum status classification for operational fulfillment lifecycle execution."""
    READY_TO_PICK = "READY_TO_PICK"
    PICKED = "PICKED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"


class FulfillmentItemModel(BaseModel):
    """Domain model representing an operational item within a fulfillment task."""
    product_id: str = Field(..., description="ObjectId reference to target Product")
    quantity: int = Field(..., description="Authoritative order quantity required")
    picked_quantity: int = Field(default=0, description="Quantity successfully picked")
    packed_quantity: int = Field(default=0, description="Quantity successfully packed")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


class FulfillmentModel(BaseModel):
    """Domain model representing operational fulfillment execution of a customer order."""
    id: Optional[str] = Field(default=None, alias="_id")
    order_id: str = Field(..., description="ObjectId reference to target Order")
    order_number: str = Field(..., description="Unique order business reference string")
    warehouse_id: str = Field(..., description="ObjectId reference to target Warehouse")
    status: FulfillmentStatus = Field(default=FulfillmentStatus.READY_TO_PICK, description="Current operational status")
    items: List[FulfillmentItemModel] = Field(default_factory=list, description="Fulfillment line items")
    picked_at: Optional[datetime] = Field(default=None, description="Timestamp when order was picked")
    picked_by_user_id: Optional[str] = Field(default=None, description="User ID who picked order")
    packed_at: Optional[datetime] = Field(default=None, description="Timestamp when order was packed")
    packed_by_user_id: Optional[str] = Field(default=None, description="User ID who packed order")
    shipped_at: Optional[datetime] = Field(default=None, description="Timestamp when order was shipped")
    shipped_by_user_id: Optional[str] = Field(default=None, description="User ID who shipped order")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
