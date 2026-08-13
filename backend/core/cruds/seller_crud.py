from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.seller_model import SellerModel

logger = get_logger(__name__)


class SellerCRUD:
    """Database persistence wrapper for Seller entity operations.
    Handles MongoDB CRUD queries for seller client documents.
    """

    @property
    def collection(self):
        """Retrieves the sellers MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB sellers collection object.
        """
        return DatabaseManager.get_db()["sellers"]

    async def create_seller(self, seller: SellerModel) -> SellerModel:
        """Inserts a new seller document into the database.
        Returns the created seller model with assigned MongoDB ObjectId.

        Args:
            seller (SellerModel): Seller domain data to create.

        Returns:
            SellerModel: The created seller instance.
        """
        logger.info(f"Executing SellerCRUD.create_seller for code {seller.code}")
        seller.code = seller.code.upper().strip()
        doc = seller.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        seller.id = str(result.inserted_id)
        return seller

    async def get_by_id(self, seller_id: str) -> Optional[SellerModel]:
        """Retrieves a seller document by string ObjectId.
        Returns None if no matching seller is found.

        Args:
            seller_id (str): String representation of seller ObjectId.

        Returns:
            Optional[SellerModel]: Seller model instance if found.
        """
        logger.info(f"Executing SellerCRUD.get_by_id for {seller_id}")
        if not ObjectId.is_valid(seller_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(seller_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return SellerModel(**doc)

    async def get_by_code(self, code: str) -> Optional[SellerModel]:
        """Retrieves a seller document by unique seller business code.
        Returns None if no matching seller exists.

        Args:
            code (str): The unique seller code string.

        Returns:
            Optional[SellerModel]: Seller model instance if found.
        """
        logger.info(f"Executing SellerCRUD.get_by_code for {code}")
        normalized_code = code.upper().strip()
        doc = await self.collection.find_one({"code": normalized_code})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return SellerModel(**doc)

    async def update_seller(self, seller_id: str, update_data: dict) -> Optional[SellerModel]:
        """Updates specific fields of an existing seller document.
        Maintains updated_at timestamp and returns updated seller model.

        Args:
            seller_id (str): String representation of seller ObjectId.
            update_data (dict): Dictionary of field updates.

        Returns:
            Optional[SellerModel]: Updated seller model instance if found.
        """
        logger.info(f"Executing SellerCRUD.update_seller for {seller_id}")
        if not ObjectId.is_valid(seller_id):
            return None
        if "code" in update_data:
            update_data["code"] = update_data["code"].upper().strip()
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(seller_id)},
            {"$set": update_data},
            return_document=True,
        )
        if not result:
            return None
        result["_id"] = str(result["_id"])
        return SellerModel(**result)

    async def list_sellers(self) -> List[SellerModel]:
        """Retrieves all registered seller documents.
        Returns a list of all seller models.

        Returns:
            List[SellerModel]: List of all sellers in the system.
        """
        logger.info("Executing SellerCRUD.list_sellers")
        cursor = self.collection.find({})
        sellers = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            sellers.append(SellerModel(**doc))
        return sellers
