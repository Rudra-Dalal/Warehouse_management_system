from typing import List, Optional
from pydantic import BaseModel, Field


class FulfillmentCreateRequest(BaseModel):
    """Request payload to initiate fulfillment execution for a confirmed order."""
    order_id: str = Field(..., description="ObjectId string reference to target CONFIRMED order")


class PickItemRequest(BaseModel):
    """Request item detail payload for picking operation."""
    product_id: str = Field(..., description="ObjectId reference to target Product")
    quantity: int = Field(..., gt=0, description="Picked quantity (> 0)")


class PickFulfillmentRequest(BaseModel):
    """Request payload to perform picking for a fulfillment task."""
    items: List[PickItemRequest] = Field(..., min_length=1, description="List of items and quantities being picked")


class PackFulfillmentRequest(BaseModel):
    """Request payload to perform packing for a picked fulfillment task."""
    note: Optional[str] = Field(default=None, description="Optional packing notes")


class ShipFulfillmentRequest(BaseModel):
    """Request payload to finalize shipping for a packed fulfillment task."""
    tracking_number: Optional[str] = Field(default=None, description="Optional internal tracking reference string")
