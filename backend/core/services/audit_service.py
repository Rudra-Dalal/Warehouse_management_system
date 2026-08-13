from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from core.cruds.audit_crud import AuditCRUD
from core.models.audit_log_model import AuditAction, AuditLogModel
from commons.logger import logger


class AuditService:
    """Service layer for creating, orchestrating, and querying operational audit logs."""

    def __init__(self, audit_crud: Optional[AuditCRUD] = None):
        self.audit_crud = audit_crud or AuditCRUD()

    async def record_event(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        session=None,
    ) -> AuditLogModel:
        """Constructs and persists an audit log record, supporting optional transaction sessions.

        Args:
            action (AuditAction): Controlled action enum.
            entity_type (str): Category string of entity.
            entity_id (str): ID of target entity.
            user_id (Optional[str]): Performing user ID.
            warehouse_id (Optional[str]): Warehouse ObjectId string.
            warehouse_code (Optional[str]): Warehouse business code (RENO/COLUMBUS).
            reference_type (Optional[str]): Reference entity type string.
            reference_id (Optional[str]): Reference entity ID.
            previous_state (Optional[Dict[str, Any]]): Pre-operation state snapshot.
            new_state (Optional[Dict[str, Any]]): Post-operation state snapshot.
            metadata (Optional[Dict[str, Any]]): Operational metadata dictionary.
            success (bool): Success flag.
            error_code (Optional[str]): Error code string if failed.
            session (Optional[AsyncClientSession]): MongoDB session for multi-doc transactions.

        Returns:
            AuditLogModel: Persisted audit log model.
        """
        logger.info(
            f"Executing AuditService.record_event: action={action.value}, "
            f"entity={entity_type}:{entity_id}, user={user_id}"
        )
        audit_log = AuditLogModel(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            warehouse_id=warehouse_id,
            warehouse_code=warehouse_code,
            reference_type=reference_type,
            reference_id=reference_id,
            previous_state=previous_state,
            new_state=new_state,
            metadata=metadata or {},
            success=success,
            error_code=error_code,
        )
        return await self.audit_crud.create_audit_log(audit_log, session=session)

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
    ) -> Tuple[List[AuditLogModel], int]:
        """Queries audit logs with pagination and multi-parameter filtering.

        Returns:
            Tuple[List[AuditLogModel], int]: (List of records, total count matching filter).
        """
        logger.info("Executing AuditService.list_audit_logs")
        filter_dict: Dict[str, Any] = {}

        if action:
            filter_dict["action"] = action
        if entity_type:
            filter_dict["entity_type"] = entity_type
        if entity_id:
            filter_dict["entity_id"] = entity_id
        if user_id:
            filter_dict["user_id"] = user_id
        if warehouse_code:
            filter_dict["warehouse_code"] = warehouse_code.upper()
        if reference_type:
            filter_dict["reference_type"] = reference_type
        if reference_id:
            filter_dict["reference_id"] = reference_id
        if success is not None:
            filter_dict["success"] = success

        if start_date or end_date:
            date_filter: Dict[str, Any] = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            filter_dict["created_at"] = date_filter

        records = await self.audit_crud.list_audit_logs(
            filter_dict=filter_dict, limit=limit, offset=offset
        )
        total_count = await self.audit_crud.count_audit_logs(filter_dict=filter_dict)
        return records, total_count

    async def get_by_id(self, audit_id: str) -> Optional[AuditLogModel]:
        """Retrieves a single audit log record by ID."""
        logger.info(f"Executing AuditService.get_by_id for ID '{audit_id}'")
        return await self.audit_crud.get_by_id(audit_id)
