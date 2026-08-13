from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from pymongo import ReturnDocument

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
        self, product_id: str, warehouse_id: str, session=None
    ) -> Optional[InventoryModel]:
        """Retrieves an inventory record for a specific product at a specific warehouse.

        Args:
            product_id (str): String representation of product ObjectId.
            warehouse_id (str): String representation of warehouse ObjectId.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            Optional[InventoryModel]: Inventory model instance if found.
        """
        logger.info(
            f"Executing InventoryCRUD.get_by_product_and_warehouse for product {product_id} "
            f"at warehouse {warehouse_id}"
        )
        doc = await self.collection.find_one(
            {"product_id": product_id, "warehouse_id": warehouse_id},
            session=session,
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

    async def reserve_inventory_atomic(
        self,
        inventory_id: str,
        requested_quantity: int,
        session=None,
    ) -> Optional[InventoryModel]:
        """Atomically reserves stock using a single MongoDB find_one_and_update operation.
        Ensures availability check and quantity updates happen atomically in the database filter.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            requested_quantity (int): Number of units to reserve (> 0).
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[InventoryModel]: Updated inventory model if successful, None if stock < requested or missing ID.
        """
        logger.info(
            f"Executing InventoryCRUD.reserve_inventory_atomic for ID {inventory_id} "
            f"requested_quantity={requested_quantity}"
        )
        if requested_quantity <= 0 or not ObjectId.is_valid(inventory_id):
            return None

        result = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(inventory_id),
                "available_quantity": {"$gte": requested_quantity},
            },
            {
                "$inc": {
                    "available_quantity": -requested_quantity,
                    "reserved_quantity": requested_quantity,
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

        if not result:
            return None
        result["_id"] = str(result["_id"])
        return InventoryModel(**result)

    async def consume_reservation_atomic(
        self,
        inventory_id: str,
        picked_quantity: int,
        session=None,
    ) -> Optional[InventoryModel]:
        """Atomically consumes reserved stock during order picking.
        Decrements reserved_quantity by picked_quantity without modifying available_quantity.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            picked_quantity (int): Number of reserved units to consume (> 0).
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[InventoryModel]: Updated inventory model if successful, None if reserved_quantity < picked_quantity or invalid ID.
        """
        logger.info(
            f"Executing InventoryCRUD.consume_reservation_atomic for ID {inventory_id} "
            f"picked_quantity={picked_quantity}"
        )
        if picked_quantity <= 0 or not ObjectId.is_valid(inventory_id):
            return None

        result = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(inventory_id),
                "reserved_quantity": {"$gte": picked_quantity},
            },
            {
                "$inc": {
                    "reserved_quantity": -picked_quantity,
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

        if not result:
            return None
        result["_id"] = str(result["_id"])
        return InventoryModel(**result)

    async def unreserve_inventory_atomic(
        self,
        inventory_id: str,
        quantity: int,
        session=None,
    ) -> Optional[InventoryModel]:
        """Atomically unreserves stock by moving quantity back from reserved_quantity to available_quantity.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            quantity (int): Number of reserved units to unreserve (> 0).
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[InventoryModel]: Updated inventory model if successful, None if invalid or reserved stock < quantity.
        """
        logger.info(
            f"Executing InventoryCRUD.unreserve_inventory_atomic for ID {inventory_id} "
            f"quantity={quantity}"
        )
        if quantity <= 0 or not ObjectId.is_valid(inventory_id):
            return None

        result = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(inventory_id),
                "reserved_quantity": {"$gte": quantity},
            },
            {
                "$inc": {
                    "available_quantity": quantity,
                    "reserved_quantity": -quantity,
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

        if not result:
            return None
        result["_id"] = str(result["_id"])
        return InventoryModel(**result)

    async def increment_inventory_atomic(
        self,
        product_id: str,
        warehouse_id: str,
        quantity: int,
        session=None,
    ) -> InventoryModel:
        """Atomically increments available_quantity for a product at a warehouse.
        If no inventory record exists, creates an initial record.

        Args:
            product_id (str): Product ObjectId string.
            warehouse_id (str): Warehouse ObjectId string.
            quantity (int): Received stock quantity to increment (> 0).
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            InventoryModel: Updated or created inventory model instance.
        """
        logger.info(
            f"Executing InventoryCRUD.increment_inventory_atomic for product {product_id} "
            f"at warehouse {warehouse_id} quantity={quantity}"
        )
        now = datetime.now(timezone.utc)
        result = await self.collection.find_one_and_update(
            {"product_id": product_id, "warehouse_id": warehouse_id},
            {
                "$inc": {"available_quantity": quantity},
                "$set": {"updated_at": now},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if result:
            result["_id"] = str(result["_id"])
            return InventoryModel(**result)

        # Record does not exist -> Create initial inventory
        initial_inv = InventoryModel(
            product_id=product_id,
            warehouse_id=warehouse_id,
            available_quantity=quantity,
            reserved_quantity=0,
            damaged_quantity=0,
            created_at=now,
            updated_at=now,
        )
        doc = initial_inv.model_dump(by_alias=True, exclude={"id"})
        try:
            insert_res = await self.collection.insert_one(doc, session=session)
            initial_inv.id = str(insert_res.inserted_id)
            return initial_inv
        except Exception:
            # Concurrent insert collision -> retry atomic increment
            retry_res = await self.collection.find_one_and_update(
                {"product_id": product_id, "warehouse_id": warehouse_id},
                {
                    "$inc": {"available_quantity": quantity},
                    "$set": {"updated_at": now},
                },
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if retry_res:
                retry_res["_id"] = str(retry_res["_id"])
                return InventoryModel(**retry_res)
            raise
