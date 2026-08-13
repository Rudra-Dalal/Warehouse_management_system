from typing import List
from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.inventory_movement_model import InventoryMovementModel

logger = get_logger(__name__)


class InventoryMovementCRUD:
    """Database persistence wrapper for InventoryMovement historical log events.
    Handles MongoDB queries for inventory change logs.
    """

    @property
    def collection(self):
        """Retrieves the inventory_movements MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB inventory_movements collection object.
        """
        return DatabaseManager.get_db()["inventory_movements"]

    async def create_movement(
        self, movement: InventoryMovementModel
    ) -> InventoryMovementModel:
        """Inserts a new inventory movement event log into the database.
        Returns the created movement model with assigned MongoDB ObjectId.

        Args:
            movement (InventoryMovementModel): Movement event log domain data.

        Returns:
            InventoryMovementModel: The created movement log instance.
        """
        logger.info(
            f"Executing InventoryMovementCRUD.create_movement type '{movement.movement_type}' "
            f"qty {movement.quantity} for product {movement.product_id}"
        )
        doc = movement.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        movement.id = str(result.inserted_id)
        return movement

    async def list_movements_by_context(
        self, product_id: str, warehouse_id: str
    ) -> List[InventoryMovementModel]:
        """Retrieves all inventory movement events for a specific Product and Warehouse.
        Returns a list of movement logs sorted by creation timestamp descending.

        Args:
            product_id (str): Product ObjectId string.
            warehouse_id (str): Warehouse ObjectId string.

        Returns:
            List[InventoryMovementModel]: Historical list of inventory movement logs.
        """
        logger.info(
            f"Executing InventoryMovementCRUD.list_movements_by_context "
            f"for product {product_id} at warehouse {warehouse_id}"
        )
        cursor = self.collection.find(
            {"product_id": product_id, "warehouse_id": warehouse_id}
        ).sort("created_at", -1)

        movements = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            movements.append(InventoryMovementModel(**doc))
        return movements
