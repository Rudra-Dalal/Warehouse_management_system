import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderItemModel(BaseModel):
    """Pydantic model representing a single product item line in an order."""

    product_id: str = Field(..., description="Target product ObjectId string")
    quantity: int = Field(..., gt=0, description="Quantity of product ordered")

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "60d5ec49f1b2c8b1f8c1e003",
                "quantity": 5,
            }
        }
    }


class OrderModel(BaseModel):
    """Pydantic model representing a customer order for warehouse fulfillment."""

    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId string")
    order_number: str = Field(..., description="Unique business order number identifier")
    seller_id: str = Field(..., description="Target seller ObjectId string")
    warehouse_id: str = Field(..., description="Target warehouse ObjectId string")
    status: str = Field("CONFIRMED", description="Order status: CREATED or CONFIRMED")
    items: List[OrderItemModel] = Field(..., min_length=1, description="List of order line items")
    created_by_user_id: str = Field(..., description="User ObjectId string who created the order")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp when order was created",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp when order was last updated",
    )
    confirmed_at: Optional[datetime.datetime] = Field(
        None, description="Timestamp when order inventory was confirmed"
    )

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "id": "60d5ec49f1b2c8b1f8c1e010",
                "order_number": "ORD-2026-000001",
                "seller_id": "60d5ec49f1b2c8b1f8c1e001",
                "warehouse_id": "60d5ec49f1b2c8b1f8c1e002",
                "status": "CONFIRMED",
                "items": [{"product_id": "60d5ec49f1b2c8b1f8c1e003", "quantity": 5}],
                "created_by_user_id": "60d5ec49f1b2c8b1f8c1e000",
            }
        },
    }
