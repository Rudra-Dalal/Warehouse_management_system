from typing import Optional
from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    """Request schema for creating a new product catalog item.
    Validates required SKU, product name, seller ID, and optional UPC string.
    """

    sku: str = Field(..., min_length=2, description="Unique product SKU business identifier")
    name: str = Field(..., description="Product title / name")
    seller_id: str = Field(..., description="ObjectId string of owning Seller")
    description: Optional[str] = Field(default=None, description="Detailed product description")
    upc: Optional[str] = Field(default=None, description="UPC barcode string (preserves leading zeros)")


class ProductUpdateRequest(BaseModel):
    """Request schema for updating an existing product catalog item.
    Supports partial updates for name, description, UPC, or active flag.
    """

    name: Optional[str] = Field(default=None, description="Updated product name")
    description: Optional[str] = Field(default=None, description="Updated description")
    upc: Optional[str] = Field(default=None, description="Updated UPC string")
    is_active: Optional[bool] = Field(default=None, description="Updated active status flag")
