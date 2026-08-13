from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from core.apis.schemas.responses.audit_response import AuditResponse
from core.services.audit_service import AuditService
from commons.logger import logger


class AuditController:
    """Controller layer handling HTTP operations for audit logs."""

    def __init__(self, audit_service: Optional[AuditService] = None):
        self.audit_service = audit_service or AuditService()

    async def list_audit_logs(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditResponse]:
        """Lists audit log records with parameters and bounds checking."""
        logger.info("Executing AuditController.list_audit_logs")
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100",
            )
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset must be non-negative",
            )

        records, _ = await self.audit_service.list_audit_logs(
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
        return [AuditResponse(**r.model_dump(by_alias=True)) for r in records]

    async def get_audit_log(self, audit_id: str) -> AuditResponse:
        """Retrieves a single audit log by ID."""
        logger.info(f"Executing AuditController.get_audit_log for ID '{audit_id}'")
        audit_log = await self.audit_service.get_by_id(audit_id)
        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit record with ID '{audit_id}' not found",
            )
        return AuditResponse(**audit_log.model_dump(by_alias=True))

    async def get_entity_history(
        self, entity_type: str, entity_id: str, limit: int = 50, offset: int = 0
    ) -> List[AuditResponse]:
        """Retrieves audit trail history for a specific entity."""
        logger.info(f"Executing AuditController.get_entity_history for {entity_type}:{entity_id}")
        return await self.list_audit_logs(
            entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset
        )

    async def get_user_history(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[AuditResponse]:
        """Retrieves audit trail history for operations performed by a specific user."""
        logger.info(f"Executing AuditController.get_user_history for user {user_id}")
        return await self.list_audit_logs(user_id=user_id, limit=limit, offset=offset)

    async def get_reference_history(
        self, reference_type: str, reference_id: str, limit: int = 50, offset: int = 0
    ) -> List[AuditResponse]:
        """Retrieves audit trail history for a specific reference operation context."""
        logger.info(f"Executing AuditController.get_reference_history for {reference_type}:{reference_id}")
        return await self.list_audit_logs(
            reference_type=reference_type, reference_id=reference_id, limit=limit, offset=offset
        )
