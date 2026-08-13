from typing import Any, Dict, List, Optional
from bson import ObjectId
from core.database.database import db_manager
from core.models.audit_log_model import AuditLogModel
from commons.logger import logger


class AuditCRUD:
    """Data Access Object for immutable audit logs in MongoDB.
    Performs append-only insertion and rich query filtering.
    """

    def __init__(self):
        self.collection = db_manager.db["audit_logs"]

    async def create_audit_log(
        self, audit_log: AuditLogModel, session=None
    ) -> AuditLogModel:
        """Inserts a new immutable audit log record. Accepts an optional MongoDB session.

        Args:
            audit_log (AuditLogModel): Audit log model instance.
            session (Optional[AsyncClientSession]): MongoDB session for transaction support.

        Returns:
            AuditLogModel: Created audit log record with assigned _id.
        """
        logger.info(
            f"Executing AuditCRUD.create_audit_log for action '{audit_log.action}' "
            f"on {audit_log.entity_type}:{audit_log.entity_id}"
        )
        doc = audit_log.model_dump(by_alias=True, exclude_none=True)
        if "_id" in doc and doc["_id"] is None:
            del doc["_id"]

        result = await self.collection.insert_one(doc, session=session)
        doc["_id"] = str(result.inserted_id)
        return AuditLogModel(**doc)

    async def get_by_id(self, audit_id: str) -> Optional[AuditLogModel]:
        """Retrieves a specific audit record by string ObjectId.

        Args:
            audit_id (str): String representation of audit ObjectId.

        Returns:
            Optional[AuditLogModel]: Audit log model if found.
        """
        logger.info(f"Executing AuditCRUD.get_by_id: {audit_id}")
        if not ObjectId.is_valid(audit_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(audit_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return AuditLogModel(**doc)

    async def list_audit_logs(
        self,
        filter_dict: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditLogModel]:
        """Lists audit log records with filter constraints, paginated, sorted newest first.

        Args:
            filter_dict (dict): PyMongo filter specification.
            limit (int): Maximum records to return.
            offset (int): Records to skip for pagination.

        Returns:
            List[AuditLogModel]: Matching audit log instances.
        """
        logger.info(
            f"Executing AuditCRUD.list_audit_logs with filters {filter_dict}, "
            f"limit={limit}, offset={offset}"
        )
        cursor = (
            self.collection.find(filter_dict)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(AuditLogModel(**doc))
        return results

    async def count_audit_logs(self, filter_dict: Dict[str, Any]) -> int:
        """Counts total audit log documents matching the filter criteria.

        Args:
            filter_dict (dict): PyMongo filter specification.

        Returns:
            int: Count of matching documents.
        """
        logger.info(f"Executing AuditCRUD.count_audit_logs with filters {filter_dict}")
        return await self.collection.count_documents(filter_dict)
