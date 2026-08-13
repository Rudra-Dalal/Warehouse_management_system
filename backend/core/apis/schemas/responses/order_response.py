import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderItemResponse(BaseModel):
    """Response payload schema for an enriched order line item."""

    product_id: str = Field(..., description="Target product ObjectId string")
    sku: Optional[str] = Field(None, description="Product SKU code")
    product_name: Optional[str] = Field(None, description="Product display name")
    quantity: int = Field(..., description="Ordered quantity")

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "60d5ec49f1b2c8b1f8c1e003",
                "sku": "PROD-SKU-100",
                "product_name": "Sample Product",
                "quantity": 5,
            }
        }
    }


class OrderResponse(BaseModel):
    """Response payload schema for a customer order."""

    id: str = Field(..., description="Order MongoDB ObjectId string")
    order_number: str = Field(..., description="Unique business order number")
    seller_id: str = Field(..., description="Seller ObjectId string")
    seller_code: Optional[str] = Field(None, description="Seller business code")
    warehouse_id: str = Field(..., description="Warehouse ObjectId string")
    warehouse_code: Optional[str] = Field(None, description="Fixed warehouse code (RENO or COLUMBUS)")
    status: str = Field(..., description="Order status: CREATED or CONFIRMED")
    items: List[OrderItemResponse] = Field(..., description="List of enriched order line items")
    created_by_user_id: str = Field(..., description="User ObjectId string who created the order")
    created_at: datetime.datetime = Field(..., description="Timestamp when order was created")
    confirmed_at: Optional[datetime.datetime] = Field(
        None, description="Timestamp when order was confirmed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ec49f1b2c8b1f8c1e010",
                "order_number": "ORD-2026-000001",
                "seller_id": "60d5ec49f1b2c8b1f8c1e001",
                "seller_code": "SELLER_001",
                "warehouse_id": "60d5ec49f1b2c8b1f8c1e002",
                "warehouse_code": "RENO",
                "status": "CONFIRMED",
                "items": [
                    {
                        "product_id": "60d5ec49f1b2c8b1f8c1e003",
                        "sku": "PROD-SKU-100",
                        "product_name": "Sample Product",
                        "quantity": 5,
                    }
                ],
                "created_by_user_id": "60d5ec49f1b2c8b1f8c1e000",
                "created_at": "2026-08-13T12:00:00Z",
                "confirmed_at": "2026-08-13T12:00:00Z",
            }
        }
    }
