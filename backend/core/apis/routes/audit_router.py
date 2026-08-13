from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from commons.auth import require_permission
from core.apis.schemas.responses.audit_response import AuditResponse
from core.controllers.audit_controller import AuditController
from core.models.user_model import UserModel

router = APIRouter(prefix="/v1/audit", tags=["Audit Trail"])
controller = AuditController()


@router.get(
    "",
    response_model=List[AuditResponse],
    summary="List operational audit trail records with filters and pagination",
)
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by AuditAction enum string"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (USER, PRODUCT, INVENTORY, ORDER, FULFILLMENT, RECEIVING)"),
    entity_id: Optional[str] = Query(None, description="Filter by target entity ID"),
    user_id: Optional[str] = Query(None, description="Filter by performing user ID"),
    warehouse_code: Optional[str] = Query(None, description="Filter by warehouse code (RENO/COLUMBUS)"),
    reference_type: Optional[str] = Query(None, description="Filter by reference context category"),
    reference_id: Optional[str] = Query(None, description="Filter by reference entity ID"),
    success: Optional[bool] = Query(None, description="Filter by operation success status"),
    start_date: Optional[datetime] = Query(None, description="Filter events after timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events before timestamp"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(require_permission("audit.read")),
):
    """Retrieves operational audit records with filtering, paginated, newest first."""
    return await controller.list_audit_logs(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        warehouse_code=warehouse_code,
        reference_type=reference_type,
        reference_id=reference_id,
        success=success,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=List[AuditResponse],
    summary="Get audit history for a specific entity",
)
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(require_permission("audit.read")),
):
    """Retrieves audit trail history for a specific entity."""
    return await controller.get_entity_history(
        entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset
    )


@router.get(
    "/user/{user_id}",
    response_model=List[AuditResponse],
    summary="Get audit history for a specific user",
)
async def get_user_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(require_permission("audit.read")),
):
    """Retrieves audit trail history for actions performed by a specific user."""
    return await controller.get_user_history(
        user_id=user_id, limit=limit, offset=offset
    )


@router.get(
    "/reference/{reference_type}/{reference_id}",
    response_model=List[AuditResponse],
    summary="Get audit history for a specific reference context",
)
async def get_reference_history(
    reference_type: str,
    reference_id: str,
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(require_permission("audit.read")),
):
    """Retrieves audit trail history for a specific reference operation."""
    return await controller.get_reference_history(
        reference_type=reference_type, reference_id=reference_id, limit=limit, offset=offset
    )


@router.get(
    "/{audit_id}",
    response_model=AuditResponse,
    summary="Get specific audit record details by ID",
)
async def get_audit_log(
    audit_id: str,
    current_user: UserModel = Depends(require_permission("audit.read")),
):
    """Retrieves a single audit log document by ID."""
    return await controller.get_audit_log(audit_id)
