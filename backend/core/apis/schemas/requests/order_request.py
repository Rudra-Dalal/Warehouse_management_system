from typing import List
from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    """Request payload schema for a single order line item."""

    product_id: str = Field(..., description="Target product ObjectId string")
    quantity: int = Field(..., gt=0, description="Quantity of product to order (> 0)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "60d5ec49f1b2c8b1f8c1e003",
                "quantity": 5,
            }
        }
    }


class OrderCreateRequest(BaseModel):
    """Request payload schema for creating a customer order."""

    order_number: str = Field(
        ..., min_length=1, description="Unique external business order number identifier"
    )
    seller_id: str = Field(..., description="Target seller ObjectId string")
    warehouse_code: str = Field(
        ..., description="Fixed warehouse code (RENO or COLUMBUS)"
    )
    items: List[OrderItemRequest] = Field(
        ..., min_length=1, description="Non-empty list of order line items"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "order_number": "ORD-2026-000001",
                "seller_id": "60d5ec49f1b2c8b1f8c1e001",
                "warehouse_code": "RENO",
                "items": [
                    {
                        "product_id": "60d5ec49f1b2c8b1f8c1e003",
                        "quantity": 5,
                    }
                ],
            }
        }
    }
