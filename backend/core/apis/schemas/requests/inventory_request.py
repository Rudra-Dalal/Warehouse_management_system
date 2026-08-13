from typing import Optional
from pydantic import BaseModel, Field


class InventoryCreateRequest(BaseModel):
    """Request schema for creating an initial warehouse inventory record.
    Validates product ID, target warehouse code (RENO or COLUMBUS), and initial available stock.
    """

    product_id: str = Field(..., description="ObjectId string of target Product")
    warehouse_code: str = Field(..., description="Warehouse code identifier (RENO or COLUMBUS)")
    initial_available: int = Field(default=0, ge=0, description="Initial available stock quantity (>= 0)")


class InventoryAdjustmentRequest(BaseModel):
    """Request schema for adjusting available inventory stock levels.
    Accepts signed quantity delta (+ for increase, - for decrease) and optional note.
    """

    quantity_delta: int = Field(..., description="Signed integer quantity delta (+ for increase, - for decrease)")
    note: Optional[str] = Field(default=None, description="Reason / note for cycle count adjustment")
