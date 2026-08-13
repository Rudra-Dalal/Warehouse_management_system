from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class InventoryModel(BaseModel):
    """Domain model representing current stock quantities for a specific Product at a specific Warehouse.
    Maintains available_quantity, reserved_quantity (Phase 4 placeholder), and damaged_quantity.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    product_id: str = Field(..., description="ObjectId reference to target Product")
    warehouse_id: str = Field(..., description="ObjectId reference to target Warehouse (RENO or COLUMBUS)")
    available_quantity: int = Field(default=0, ge=0, description="Available stock units ready for fulfillment")
    reserved_quantity: int = Field(default=0, ge=0, description="Reserved stock units allocated to orders")
    damaged_quantity: int = Field(default=0, ge=0, description="Damaged stock units unfit for sale")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
