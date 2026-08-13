from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ProductModel(BaseModel):
    """Domain model representing a product SKU stored and fulfilled by Whitfield.
    Maintains SKU, optional string UPC barcode, description, and seller relationship.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    sku: str = Field(..., description="Unique product SKU business identifier")
    name: str = Field(..., description="Product title / name")
    description: Optional[str] = Field(default=None, description="Detailed product description")
    upc: Optional[str] = Field(default=None, description="UPC barcode string (preserves leading zeros)")
    seller_id: str = Field(..., description="ObjectId reference to owning Seller document")
    is_active: bool = Field(default=True, description="Active product status flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
