from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.user_model import UserModel

logger = get_logger(__name__)


class UserCRUD:
    """Database persistence wrapper for User entity operations.
    Handles MongoDB CRUD queries for authenticated user documents.
    """

    @property
    def collection(self):
        """Retrieves the users MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB users collection object.
        """
        return DatabaseManager.get_db()["users"]

    async def create_user(self, user: UserModel) -> UserModel:
        """Inserts a new user document into the database.
        Ensures email is stored lowercased and returns created user instance.

        Args:
            user (UserModel): User domain data to create.

        Returns:
            UserModel: The created user instance.
        """
        logger.info(f"Executing UserCRUD.create_user for {user.email}")
        user.email = user.email.lower().strip()
        doc = user.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        user.id = str(result.inserted_id)
        return user

    async def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """Retrieves a user document by string ObjectId.
        Returns None if no matching user is found.

        Args:
            user_id (str): String representation of user ObjectId.

        Returns:
            Optional[UserModel]: User model instance if found.
        """
        logger.info(f"Executing UserCRUD.get_by_id for {user_id}")
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return UserModel(**doc)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Retrieves a user document by unique lowercased email address.
        Returns None if no matching user exists.

        Args:
            email (str): User email address.

        Returns:
            Optional[UserModel]: User model instance if found.
        """
        logger.info(f"Executing UserCRUD.get_by_email for {email}")
        normalized_email = email.lower().strip()
        doc = await self.collection.find_one({"email": normalized_email})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return UserModel(**doc)

    async def update_user(self, user_id: str, update_data: dict) -> Optional[UserModel]:
        """Updates specific fields of an existing user document.
        Maintains updated_at timestamp and returns updated user model.

        Args:
            user_id (str): String representation of user ObjectId.
            update_data (dict): Dictionary of field updates.

        Returns:
            Optional[UserModel]: Updated user model instance if found.
        """
        logger.info(f"Executing UserCRUD.update_user for {user_id}")
        if not ObjectId.is_valid(user_id):
            return None
        if "email" in update_data:
            update_data["email"] = update_data["email"].lower().strip()
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=True,
        )
        if not result:
            return None
        result["_id"] = str(result["_id"])
        return UserModel(**result)

    async def list_users(self) -> List[UserModel]:
        """Retrieves all registered user documents.
        Returns a list of all user models.

        Returns:
            List[UserModel]: List of all users in the system.
        """
        logger.info("Executing UserCRUD.list_users")
        cursor = self.collection.find({})
        users = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            users.append(UserModel(**doc))
        return users
