from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from core.models.audit_log_model import AuditAction


class AuditResponse(BaseModel):
    """API response DTO for exposing immutable audit log records."""
    id: str = Field(..., description="Audit record ObjectId string")
    action: AuditAction = Field(..., description="Action classification enum")
    entity_type: str = Field(..., description="Target entity category")
    entity_id: str = Field(..., description="Target entity ID")
    user_id: Optional[str] = Field(None, description="User ObjectId string who performed action")
    warehouse_id: Optional[str] = Field(None, description="Warehouse ObjectId string")
    warehouse_code: Optional[str] = Field(None, description="Warehouse business code (RENO/COLUMBUS)")
    reference_type: Optional[str] = Field(None, description="Reference category (ORDER, RECEIVING, FULFILLMENT)")
    reference_id: Optional[str] = Field(None, description="Reference entity ID")
    previous_state: Optional[Dict[str, Any]] = Field(None, description="State snapshot prior to operation")
    new_state: Optional[Dict[str, Any]] = Field(None, description="State snapshot resulting from operation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe operational metadata dictionary")
    success: bool = Field(..., description="Success flag")
    error_code: Optional[str] = Field(None, description="Error code if operation failed")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {
        "populate_by_name": True,
    }
