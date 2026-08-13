import enum
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditAction(str, enum.Enum):
    """Controlled enum classification for operational audit trail events."""
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"

    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"

    SELLER_CREATED = "SELLER_CREATED"
    SELLER_UPDATED = "SELLER_UPDATED"

    INVENTORY_CREATED = "INVENTORY_CREATED"
    INVENTORY_ADJUSTED = "INVENTORY_ADJUSTED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"

    RECEIVING_CREATED = "RECEIVING_CREATED"
    RECEIVING_COMPLETED = "RECEIVING_COMPLETED"

    ORDER_CREATED = "ORDER_CREATED"
    ORDER_RESERVED = "ORDER_RESERVED"

    FULFILLMENT_CREATED = "FULFILLMENT_CREATED"
    FULFILLMENT_PICKED = "FULFILLMENT_PICKED"
    FULFILLMENT_PACKED = "FULFILLMENT_PACKED"
    FULFILLMENT_SHIPPED = "FULFILLMENT_SHIPPED"

    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"


class AuditLogModel(BaseModel):
    """Domain model representing an immutable, append-only operational audit trail record."""
    id: Optional[str] = Field(default=None, alias="_id")
    action: AuditAction = Field(..., description="Action classification enum")
    entity_type: str = Field(..., description="Target entity category (USER, PRODUCT, INVENTORY, ORDER, FULFILLMENT, RECEIVING, SELLER)")
    entity_id: str = Field(..., description="Target entity ID")
    user_id: Optional[str] = Field(default=None, description="User ObjectId string who performed action")
    warehouse_id: Optional[str] = Field(default=None, description="Warehouse ObjectId string")
    warehouse_code: Optional[str] = Field(default=None, description="Warehouse code (RENO/COLUMBUS)")
    reference_type: Optional[str] = Field(default=None, description="Reference context category (ORDER, RECEIVING, FULFILLMENT)")
    reference_id: Optional[str] = Field(default=None, description="Reference entity ID")
    previous_state: Optional[Dict[str, Any]] = Field(default=None, description="Business state snapshot prior to operation")
    new_state: Optional[Dict[str, Any]] = Field(default=None, description="Business state snapshot resulting from operation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe operational metadata")
    success: bool = Field(default=True, description="Indicates if operation succeeded or failed")
    error_code: Optional[str] = Field(default=None, description="Error classification string if operation failed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
