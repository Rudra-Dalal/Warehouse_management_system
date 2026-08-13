from typing import Dict, List, Optional
from commons.logger import get_logger
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.models.inventory_model import InventoryModel
from core.models.inventory_movement_model import InventoryMovementModel

logger = get_logger(__name__)


class InventoryReservationService:
    """Service layer encapsulating atomic inventory stock reservation and historical movement logging."""

    def __init__(self):
        self.inventory_crud = InventoryCRUD()
        self.inventory_movement_crud = InventoryMovementCRUD()

    async def reserve_item_atomic(
        self,
        inventory_id: str,
        requested_quantity: int,
        user_id: str,
        reference_type: str = "RESERVATION",
        reference_id: Optional[str] = None,
        session=None,
    ) -> Optional[InventoryModel]:
        """Atomically reserves stock for a single inventory record using Phase 4 find_one_and_update.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            requested_quantity (int): Number of stock units to reserve (> 0).
            user_id (str): User ObjectId string performing the reservation.
            reference_type (str): Context reference type (RESERVATION or ORDER).
            reference_id (Optional[str]): Target reference ObjectId string.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[InventoryModel]: Updated inventory model if successful, None if insufficient stock.
        """
        logger.info(
            f"Executing InventoryReservationService.reserve_item_atomic for inv {inventory_id} "
            f"qty={requested_quantity} user={user_id}"
        )

        if requested_quantity <= 0:
            logger.warning(f"Invalid requested quantity '{requested_quantity}' <= 0 rejected")
            return None

        # Pass session handle to InventoryCRUD for transaction participation
        updated_inv = await self.inventory_crud.reserve_inventory_atomic(
            inventory_id=inventory_id,
            requested_quantity=requested_quantity,
            session=session,
        )

        if not updated_inv:
            return None

        # Log RESERVATION movement with signed negative delta in the same session
        await self.inventory_movement_crud.create_movement(
            movement=InventoryMovementModel(
                product_id=updated_inv.product_id,
                warehouse_id=updated_inv.warehouse_id,
                movement_type="RESERVATION",
                quantity=-requested_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user_id,
            ),
            session=session,
        )

        return updated_inv

    async def reserve_multi_items_atomic(
        self,
        items: List[Dict],
        user_id: str,
        reference_type: str = "ORDER",
        reference_id: Optional[str] = None,
        session=None,
    ) -> List[InventoryModel]:
        """Atomically reserves stock for multiple inventory items under transactional semantics.

        Args:
            items (List[Dict]): List of dicts containing 'inventory_id' and 'quantity'.
            user_id (str): User ObjectId string performing the reservation.
            reference_type (str): Movement reference type (ORDER).
            reference_id (Optional[str]): Order ObjectId string.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            List[InventoryModel]: List of updated inventory records.

        Raises:
            ValueError: If any item fails reservation due to insufficient available stock.
        """
        logger.info(f"Executing InventoryReservationService.reserve_multi_items_atomic for {len(items)} items")
        reserved_records = []

        for item_data in items:
            inv_id = item_data["inventory_id"]
            qty = item_data["quantity"]

            updated_inv = await self.reserve_item_atomic(
                inventory_id=inv_id,
                requested_quantity=qty,
                user_id=user_id,
                reference_type=reference_type,
                reference_id=reference_id,
                session=session,
            )

            if not updated_inv:
                logger.warning(
                    f"Multi-item reservation failed on inventory {inv_id}. Raising ValueError for transaction abort."
                )
                raise ValueError(f"Insufficient available stock for inventory ID '{inv_id}'")

            reserved_records.append(updated_inv)

        return reserved_records
