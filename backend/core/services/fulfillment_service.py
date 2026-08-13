from typing import List, Dict, Any
from commons.logger import get_logger
from core.models.fulfillment_model import FulfillmentItemModel, FulfillmentModel, FulfillmentStatus

logger = get_logger(__name__)


class FulfillmentService:
    """Domain logic service enforcing status transition state machine rules and pick/pack/ship validation."""

    VALID_TRANSITIONS = {
        FulfillmentStatus.READY_TO_PICK: {FulfillmentStatus.PICKED},
        FulfillmentStatus.PICKED: {FulfillmentStatus.PACKED},
        FulfillmentStatus.PACKED: {FulfillmentStatus.SHIPPED},
        FulfillmentStatus.SHIPPED: set(),
    }

    def validate_transition(
        self,
        current_status: FulfillmentStatus,
        target_status: FulfillmentStatus,
    ) -> None:
        """Validates if transitioning from current_status to target_status is allowed.

        Args:
            current_status (FulfillmentStatus): Current fulfillment status.
            target_status (FulfillmentStatus): Desired target status.

        Raises:
            ValueError: If the state transition is invalid.
        """
        logger.info(f"Executing FulfillmentService.validate_transition: {current_status} -> {target_status}")
        allowed = self.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise ValueError(
                f"Invalid fulfillment status transition from '{current_status.value}' to '{target_status.value}'"
            )

    def validate_and_build_pick_items(
        self,
        fulfillment: FulfillmentModel,
        pick_items_data: List[Dict[str, Any]],
    ) -> List[FulfillmentItemModel]:
        """Validates requested pick quantities against authoritative order items.

        MVP Requirement: Complete picking (picked_quantity == required quantity).

        Args:
            fulfillment (FulfillmentModel): Target fulfillment entity.
            pick_items_data (List[Dict[str, Any]]): Pick request items payload.

        Returns:
            List[FulfillmentItemModel]: Updated fulfillment items with pick progress.

        Raises:
            ValueError: If quantities are invalid or complete picking is not satisfied.
        """
        logger.info(f"Executing FulfillmentService.validate_and_build_pick_items for fulfillment '{fulfillment.id}'")
        
        # Build map of product_id -> requested pick quantity
        pick_map = {}
        for item_data in pick_items_data:
            pid = item_data.get("product_id")
            qty = item_data.get("quantity", 0)
            if not pid:
                raise ValueError("Each pick item must specify a valid product_id")
            if qty <= 0:
                raise ValueError(f"Pick quantity for product '{pid}' must be positive")
            pick_map[pid] = qty

        updated_items = []
        for existing_item in fulfillment.items:
            pid = existing_item.product_id
            if pid not in pick_map:
                raise ValueError(f"Missing pick quantity for required product ID '{pid}'")
            
            requested_pick_qty = pick_map[pid]
            if requested_pick_qty != existing_item.quantity:
                raise ValueError(
                    f"Incomplete pick for product '{pid}': requested {requested_pick_qty}, "
                    f"required {existing_item.quantity}. Full picking is required."
                )

            updated_items.append(
                FulfillmentItemModel(
                    product_id=pid,
                    quantity=existing_item.quantity,
                    picked_quantity=requested_pick_qty,
                    packed_quantity=existing_item.packed_quantity,
                )
            )

        # Ensure no extra unexpected products were passed
        fulfillment_pids = {it.product_id for it in fulfillment.items}
        for pid in pick_map:
            if pid not in fulfillment_pids:
                raise ValueError(f"Product ID '{pid}' does not belong to fulfillment '{fulfillment.id}'")

        return updated_items
