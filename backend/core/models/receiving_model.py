import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReceivingItemModel(BaseModel):
    """Domain model representing an individual product line item in a receiving shipment."""

    product_id: str = Field(..., description="Target Product ObjectId string")
    quantity: int = Field(..., gt=0, description="Quantity received (> 0)")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReceivingShipmentModel(BaseModel):
    """Domain model representing an inbound warehouse receiving shipment."""

    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId string")
    receiving_reference: str = Field(..., description="Unique receiving shipment reference code (e.g. WH-REC-001)")
    warehouse_id: str = Field(..., description="Target Warehouse ObjectId string")
    seller_id: str = Field(..., description="Owner Seller ObjectId string")
    status: str = Field("PROCESSING", description="Shipment status: PROCESSING, RECEIVED, or FAILED")
    items: List[ReceivingItemModel] = Field(..., min_length=1, description="List of product line items")
    received_by_user_id: str = Field(..., description="User ObjectId string who processed the receiving")
    received_at: Optional[datetime.datetime] = Field(None, description="Timestamp when receiving completed")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Shipment creation timestamp",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Shipment last update timestamp",
    )

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
