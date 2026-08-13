from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FulfillmentItemResponse(BaseModel):
    """Response DTO for an item within a fulfillment task."""
    product_id: str = Field(..., description="Target Product ObjectId string")
    sku: Optional[str] = Field(default=None, description="Product SKU code")
    product_name: Optional[str] = Field(default=None, description="Product display name")
    quantity: int = Field(..., description="Ordered quantity required")
    picked_quantity: int = Field(..., description="Quantity picked")
    packed_quantity: int = Field(..., description="Quantity packed")


class FulfillmentResponse(BaseModel):
    """Response DTO for an operational fulfillment execution record."""
    id: str = Field(..., description="Fulfillment ObjectId string")
    order_id: str = Field(..., description="Order ObjectId string")
    order_number: str = Field(..., description="Order business reference string")
    warehouse_id: str = Field(..., description="Warehouse ObjectId string")
    warehouse_code: Optional[str] = Field(default=None, description="Warehouse code (RENO/COLUMBUS)")
    status: str = Field(..., description="Operational status (READY_TO_PICK, PICKED, PACKED, SHIPPED)")
    items: List[FulfillmentItemResponse] = Field(..., description="List of fulfillment line items")
    picked_at: Optional[datetime] = Field(default=None, description="Timestamp when picked")
    picked_by_user_id: Optional[str] = Field(default=None, description="User ID who picked order")
    packed_at: Optional[datetime] = Field(default=None, description="Timestamp when packed")
    packed_by_user_id: Optional[str] = Field(default=None, description="User ID who packed order")
    shipped_at: Optional[datetime] = Field(default=None, description="Timestamp when shipped")
    shipped_by_user_id: Optional[str] = Field(default=None, description="User ID who shipped order")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
