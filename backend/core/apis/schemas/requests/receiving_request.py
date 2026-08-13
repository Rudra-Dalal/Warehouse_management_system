from typing import List
from pydantic import BaseModel, ConfigDict, Field


class ReceivingItemRequest(BaseModel):
    """Schema for an individual receiving line item request."""

    product_id: str = Field(..., min_length=1, description="Target Product ObjectId string")
    quantity: int = Field(..., gt=0, description="Quantity to receive (> 0)")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReceivingCreateRequest(BaseModel):
    """Schema for submitting an inbound warehouse receiving shipment."""

    receiving_reference: str = Field(
        ..., min_length=1, description="Unique shipment reference code (e.g. WH-REC-001)"
    )
    warehouse_code: str = Field(
        ..., min_length=1, description="Fixed target warehouse code (RENO or COLUMBUS)"
    )
    seller_id: str = Field(..., min_length=1, description="Target Seller ObjectId string")
    items: List[ReceivingItemRequest] = Field(
        ..., min_length=1, description="List of product line items to receive"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
