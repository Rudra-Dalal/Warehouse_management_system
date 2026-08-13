from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.role_model import RoleModel

logger = get_logger(__name__)


class RoleCRUD:
    """Database persistence wrapper for Role entity operations.
    Handles MongoDB CRUD queries for security role documents.
    """

    @property
    def collection(self):
        """Retrieves the roles MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB roles collection object.
        """
        return DatabaseManager.get_db()["roles"]

    async def create_role(self, role: RoleModel) -> RoleModel:
        """Inserts a new security role document into the database.
        Returns the created role model with assigned MongoDB ObjectId.

        Args:
            role (RoleModel): Security role domain data to create.

        Returns:
            RoleModel: The created role instance.
        """
        logger.info("Executing RoleCRUD.create_role")
        doc = role.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        role.id = str(result.inserted_id)
        return role

    async def get_by_id(self, role_id: str) -> Optional[RoleModel]:
        """Retrieves a role document by string ObjectId.
        Returns None if no matching role is found.

        Args:
            role_id (str): String representation of role ObjectId.

        Returns:
            Optional[RoleModel]: Role model instance if found.
        """
        logger.info(f"Executing RoleCRUD.get_by_id for {role_id}")
        if not ObjectId.is_valid(role_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(role_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return RoleModel(**doc)

    async def get_by_name(self, name: str) -> Optional[RoleModel]:
        """Retrieves a role document by unique role name.
        Returns None if no matching role exists.

        Args:
            name (str): The unique role name.

        Returns:
            Optional[RoleModel]: Role model instance if found.
        """
        logger.info(f"Executing RoleCRUD.get_by_name for {name}")
        doc = await self.collection.find_one({"name": name})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return RoleModel(**doc)

    async def list_roles(self) -> List[RoleModel]:
        """Retrieves all registered security roles.
        Returns a list of all security role models.

        Returns:
            List[RoleModel]: List of all roles in the system.
        """
        logger.info("Executing RoleCRUD.list_roles")
        cursor = self.collection.find({})
        roles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            roles.append(RoleModel(**doc))
        return roles
