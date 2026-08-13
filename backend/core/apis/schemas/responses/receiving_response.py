import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReceivingItemResponse(BaseModel):
    """Schema for a line item in a receiving response."""

    product_id: str = Field(..., description="Product ObjectId string")
    sku: Optional[str] = Field(None, description="Product SKU code")
    product_name: Optional[str] = Field(None, description="Product display name")
    quantity: int = Field(..., description="Received line item quantity")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReceivingResponse(BaseModel):
    """Schema for an inbound receiving shipment API response."""

    id: str = Field(..., description="Receiving Shipment ObjectId string")
    receiving_reference: str = Field(..., description="Unique receiving reference code")
    warehouse_id: str = Field(..., description="Warehouse ObjectId string")
    warehouse_code: Optional[str] = Field(None, description="Fixed warehouse code (RENO or COLUMBUS)")
    seller_id: str = Field(..., description="Seller ObjectId string")
    seller_code: Optional[str] = Field(None, description="Seller code")
    status: str = Field(..., description="Shipment status (PROCESSING or RECEIVED)")
    items: List[ReceivingItemResponse] = Field(..., description="Received line items")
    received_by_user_id: str = Field(..., description="User ObjectId string who processed the receiving")
    received_at: Optional[datetime.datetime] = Field(None, description="Completion timestamp")
    created_at: datetime.datetime = Field(..., description="Shipment creation timestamp")

    model_config = ConfigDict(arbitrary_types_allowed=True)
