from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.inventory_model import InventoryModel

logger = get_logger(__name__)


class InventoryCRUD:
    """Database persistence wrapper for Inventory state entity operations.
    Handles MongoDB queries for warehouse stock records.
    """

    @property
    def collection(self):
        """Retrieves the inventory MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB inventory collection object.
        """
        return DatabaseManager.get_db()["inventory"]

    async def create_inventory(self, inventory: InventoryModel) -> InventoryModel:
        """Inserts a new warehouse inventory document into the database.
        Returns the created inventory model with assigned MongoDB ObjectId.

        Args:
            inventory (InventoryModel): Inventory domain data to create.

        Returns:
            InventoryModel: The created inventory instance.
        """
        logger.info(
            f"Executing InventoryCRUD.create_inventory for product {inventory.product_id} "
            f"at warehouse {inventory.warehouse_id}"
        )
        doc = inventory.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        inventory.id = str(result.inserted_id)
        return inventory

    async def get_by_id(self, inventory_id: str) -> Optional[InventoryModel]:
        """Retrieves an inventory document by string ObjectId.
        Returns None if no matching record is found.

        Args:
            inventory_id (str): String representation of inventory ObjectId.

        Returns:
            Optional[InventoryModel]: Inventory model instance if found.
        """
        logger.info(f"Executing InventoryCRUD.get_by_id for {inventory_id}")
        if not ObjectId.is_valid(inventory_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(inventory_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return InventoryModel(**doc)

    async def get_by_product_and_warehouse(
        self, product_id: str, warehouse_id: str
    ) -> Optional[InventoryModel]:
        """Retrieves an inventory record for a specific Product and Warehouse combination.
        Returns None if no matching record exists.

        Args:
            product_id (str): Product ObjectId string.
            warehouse_id (str): Warehouse ObjectId string.

        Returns:
            Optional[InventoryModel]: Inventory model instance if found.
        """
        logger.info(
            f"Executing InventoryCRUD.get_by_product_and_warehouse for product {product_id} "
            f"at warehouse {warehouse_id}"
        )
        doc = await self.collection.find_one(
            {"product_id": product_id, "warehouse_id": warehouse_id}
        )
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return InventoryModel(**doc)

    async def update_inventory(
        self, inventory_id: str, update_data: dict
    ) -> Optional[InventoryModel]:
        """Updates specific quantity fields of an existing inventory document.
        Maintains updated_at timestamp and returns updated inventory model.

        Args:
            inventory_id (str): String representation of inventory ObjectId.
            update_data (dict): Dictionary of field updates.

        Returns:
            Optional[InventoryModel]: Updated inventory model instance if found.
        """
        logger.info(f"Executing InventoryCRUD.update_inventory for {inventory_id}")
        if not ObjectId.is_valid(inventory_id):
            return None
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(inventory_id)},
            {"$set": update_data},
            return_document=True,
        )
        if not result:
            return None
        result["_id"] = str(result["_id"])
        return InventoryModel(**result)

    async def list_inventory(
        self,
        warehouse_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[InventoryModel]:
        """Retrieves inventory documents with optional warehouse_id and product_id filters.
        Returns a list of inventory models.

        Args:
            warehouse_id (Optional[str]): Optional warehouse ObjectId filter.
            product_id (Optional[str]): Optional product ObjectId filter.

        Returns:
            List[InventoryModel]: List of matching inventory records.
        """
        logger.info(
            f"Executing InventoryCRUD.list_inventory (warehouse_id={warehouse_id}, product_id={product_id})"
        )
        query = {}
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if product_id:
            query["product_id"] = product_id

        cursor = self.collection.find(query)
        records = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            records.append(InventoryModel(**doc))
        return records
