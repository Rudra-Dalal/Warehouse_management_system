from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.permission_model import PermissionModel

logger = get_logger(__name__)


class PermissionCRUD:
    """Database persistence wrapper for Permission entity operations.
    Handles MongoDB CRUD queries for system permission documents.
    """

    @property
    def collection(self):
        """Retrieves the permissions MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB permissions collection object.
        """
        return DatabaseManager.get_db()["permissions"]

    async def create_permission(self, permission: PermissionModel) -> PermissionModel:
        """Inserts a new permission document into the database.
        Returns the created permission model with assigned MongoDB ObjectId.

        Args:
            permission (PermissionModel): Permission domain data to create.

        Returns:
            PermissionModel: The created permission instance.
        """
        logger.info("Executing PermissionCRUD.create_permission")
        doc = permission.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        permission.id = str(result.inserted_id)
        return permission

    async def get_by_id(self, permission_id: str) -> Optional[PermissionModel]:
        """Retrieves a permission document by string ObjectId.
        Returns None if no matching permission is found.

        Args:
            permission_id (str): String representation of permission ObjectId.

        Returns:
            Optional[PermissionModel]: Permission model instance if found.
        """
        logger.info(f"Executing PermissionCRUD.get_by_id for {permission_id}")
        if not ObjectId.is_valid(permission_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(permission_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return PermissionModel(**doc)

    async def get_by_name(self, name: str) -> Optional[PermissionModel]:
        """Retrieves a permission document by unique permission name.
        Returns None if no matching permission exists.

        Args:
            name (str): The unique permission name.

        Returns:
            Optional[PermissionModel]: Permission model instance if found.
        """
        logger.info(f"Executing PermissionCRUD.get_by_name for {name}")
        doc = await self.collection.find_one({"name": name})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return PermissionModel(**doc)

    async def get_by_ids(self, permission_ids: List[str]) -> List[PermissionModel]:
        """Retrieves multiple permission documents by list of ObjectId strings.
        Ignores invalid ObjectId strings.

        Args:
            permission_ids (List[str]): List of permission ObjectId strings.

        Returns:
            List[PermissionModel]: List of matching permission model instances.
        """
        logger.info("Executing PermissionCRUD.get_by_ids")
        valid_object_ids = [ObjectId(pid) for pid in permission_ids if ObjectId.is_valid(pid)]
        if not valid_object_ids:
            return []
        cursor = self.collection.find({"_id": {"$in": valid_object_ids}})
        permissions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            permissions.append(PermissionModel(**doc))
        return permissions

    async def list_permissions(self) -> List[PermissionModel]:
        """Retrieves all registered system permissions.
        Returns a list of all permission models.

        Returns:
            List[PermissionModel]: List of all permissions in the system.
        """
        logger.info("Executing PermissionCRUD.list_permissions")
        cursor = self.collection.find({})
        permissions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            permissions.append(PermissionModel(**doc))
        return permissions
