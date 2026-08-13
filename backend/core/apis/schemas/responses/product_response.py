from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    """Response schema exposing public product catalog details.
    Provides product ID, SKU, title, UPC barcode string, seller ID, and timestamps.
    """

    id: str = Field(..., description="Product ObjectId string")
    sku: str = Field(..., description="Unique product SKU string")
    name: str = Field(..., description="Product title / name")
    description: Optional[str] = Field(default=None, description="Product description")
    upc: Optional[str] = Field(default=None, description="UPC barcode string")
    seller_id: str = Field(..., description="Owning Seller ObjectId string")
    is_active: bool = Field(..., description="Active product status flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
