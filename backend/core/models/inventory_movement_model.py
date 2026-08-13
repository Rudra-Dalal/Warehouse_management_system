from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class InventoryMovementModel(BaseModel):
    """Domain model representing a historical inventory modification log event.
    Tracks signed quantity delta (+ for increase, - for decrease), movement type, user, and context.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    product_id: str = Field(..., description="ObjectId reference to target Product")
    warehouse_id: str = Field(..., description="ObjectId reference to target Warehouse")
    movement_type: str = Field(..., description="Movement event classification (ADJUSTMENT, DAMAGE)")
    quantity: int = Field(..., description="Signed integer quantity delta (+ for increase, - for decrease)")
    reference_type: Optional[str] = Field(default="MANUAL_ADJUSTMENT", description="Event reference category")
    reference_id: Optional[str] = Field(default=None, description="External entity reference ID")
    user_id: str = Field(..., description="ObjectId reference to user who performed adjustment")
    note: Optional[str] = Field(default=None, description="Reason / note for adjustment")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
