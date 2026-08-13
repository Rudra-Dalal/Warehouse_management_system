from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InventoryResponse(BaseModel):
    """Response schema exposing warehouse inventory state metadata.
    Provides inventory ID, product ID, warehouse ID, quantity state counts, and metadata.
    """

    id: str = Field(..., description="Inventory ObjectId string")
    product_id: str = Field(..., description="Target Product ObjectId string")
    warehouse_id: str = Field(..., description="Target Warehouse ObjectId string")
    available_quantity: int = Field(..., description="Available stock quantity")
    reserved_quantity: int = Field(..., description="Reserved stock quantity")
    damaged_quantity: int = Field(..., description="Damaged stock quantity")
    sku: Optional[str] = Field(default=None, description="Product SKU string")
    product_name: Optional[str] = Field(default=None, description="Product title / name")
    warehouse_code: Optional[str] = Field(default=None, description="Warehouse code (RENO or COLUMBUS)")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last updated timestamp")


class InventoryMovementResponse(BaseModel):
    """Response schema exposing inventory movement change log events.
    Provides event ID, movement type, signed quantity delta, user ID, note, and timestamp.
    """

    id: str = Field(..., description="Movement log ObjectId string")
    product_id: str = Field(..., description="Product ObjectId string")
    warehouse_id: str = Field(..., description="Warehouse ObjectId string")
    movement_type: str = Field(..., description="Movement event classification (ADJUSTMENT, DAMAGE)")
    quantity: int = Field(..., description="Signed integer quantity delta (+ for increase, - for decrease)")
    reference_type: Optional[str] = Field(default=None, description="Reference event classification")
    user_id: str = Field(..., description="User ObjectId string who performed adjustment")
    note: Optional[str] = Field(default=None, description="Adjustment reason note")
    created_at: datetime = Field(..., description="Movement event creation timestamp")
