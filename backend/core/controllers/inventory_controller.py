from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status

from commons.logger import get_logger
from core.apis.schemas.requests.inventory_request import (
    InventoryAdjustmentRequest,
    InventoryCreateRequest,
    InventoryReservationRequest,
)
from core.apis.schemas.responses.inventory_response import (
    InventoryMovementResponse,
    InventoryResponse,
)
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.product_crud import ProductCRUD
from core.database.database import DatabaseManager
from core.models.audit_log_model import AuditAction
from core.models.inventory_model import InventoryModel
from core.models.inventory_movement_model import InventoryMovementModel
from core.models.user_model import UserModel
from core.services.audit_service import AuditService
from core.services.inventory_reservation_service import InventoryReservationService

logger = get_logger(__name__)


class InventoryController:
    """Business logic controller orchestrating warehouse stock levels and movement logs.
    Validates warehouse/product existence, composite uniqueness, and stock non-negative invariants.
    """

    def __init__(self):
        """Initializes InventoryController with Inventory, Product, Movement CRUDs, and ReservationService."""
        self.inventory_crud = InventoryCRUD()
        self.product_crud = ProductCRUD()
        self.movement_crud = InventoryMovementCRUD()
        self.reservation_service = InventoryReservationService()

    async def list_inventory(
        self,
        warehouse_code: Optional[str] = None,
        sku: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[InventoryResponse]:
        """Retrieves warehouse inventory records with optional warehouse, SKU, or product filters.
        Enriches responses with SKU string, product name, and warehouse code.

        Args:
            warehouse_code (Optional[str]): Warehouse code filter (RENO or COLUMBUS).
            sku (Optional[str]): Product SKU filter string.
            product_id (Optional[str]): Product ObjectId filter.

        Returns:
            List[InventoryResponse]: List of matching inventory records.
        """
        logger.info(f"Executing InventoryController.list_inventory (wh={warehouse_code}, sku={sku})")
        db = DatabaseManager.get_db()
        target_warehouse_id = None
        target_product_id = product_id

        if warehouse_code:
            wh_doc = await db["warehouses"].find_one({"code": warehouse_code.upper().strip()})
            if not wh_doc:
                return []
            target_warehouse_id = str(wh_doc["_id"])

        if sku:
            product_doc = await self.product_crud.get_by_sku(sku)
            if not product_doc:
                return []
            target_product_id = product_doc.id

        records = await self.inventory_crud.list_inventory(
            warehouse_id=target_warehouse_id,
            product_id=target_product_id,
        )

        responses = []
        for r in records:
            product = await self.product_crud.get_by_id(r.product_id)
            wh = await db["warehouses"].find_one({"_id": ObjectId(r.warehouse_id)})
            responses.append(
                InventoryResponse(
                    id=r.id,
                    product_id=r.product_id,
                    warehouse_id=r.warehouse_id,
                    available_quantity=r.available_quantity,
                    reserved_quantity=r.reserved_quantity,
                    damaged_quantity=r.damaged_quantity,
                    sku=product.sku if product else None,
                    product_name=product.name if product else None,
                    warehouse_code=wh["code"] if wh else None,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return responses

    async def get_inventory_by_id(self, inventory_id: str) -> InventoryResponse:
        """Retrieves a specific inventory record by string ObjectId.
        Raises HTTP 404 Not Found if no inventory record exists.

        Args:
            inventory_id (str): Target inventory ObjectId string.

        Returns:
            InventoryResponse: Target inventory record details.
        """
        logger.info(f"Executing InventoryController.get_inventory_by_id for {inventory_id}")
        record = await self.inventory_crud.get_by_id(inventory_id)
        if not record:
            logger.warning(f"Inventory record ID {inventory_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory record with ID '{inventory_id}' not found",
            )

        db = DatabaseManager.get_db()
        product = await self.product_crud.get_by_id(record.product_id)
        wh = await db["warehouses"].find_one({"_id": ObjectId(record.warehouse_id)})

        return InventoryResponse(
            id=record.id,
            product_id=record.product_id,
            warehouse_id=record.warehouse_id,
            available_quantity=record.available_quantity,
            reserved_quantity=record.reserved_quantity,
            damaged_quantity=record.damaged_quantity,
            sku=product.sku if product else None,
            product_name=product.name if product else None,
            warehouse_code=wh["code"] if wh else None,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create_inventory(self, request: InventoryCreateRequest) -> InventoryResponse:
        """Registers a new warehouse inventory record for a Product and Warehouse.
        Validates product and warehouse existence and composite product+warehouse uniqueness.

        Args:
            request (InventoryCreateRequest): Inventory creation parameters.

        Returns:
            InventoryResponse: The created inventory record details.
        """
        logger.info(
            f"Executing InventoryController.create_inventory for product {request.product_id} "
            f"at warehouse {request.warehouse_code}"
        )
        db = DatabaseManager.get_db()
        wh_code = request.warehouse_code.upper().strip()
        wh_doc = await db["warehouses"].find_one({"code": wh_code})
        if not wh_doc:
            logger.warning(f"Inventory creation failed: Warehouse code '{wh_code}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse with code '{wh_code}' not found",
            )
        warehouse_id = str(wh_doc["_id"])

        product = await self.product_crud.get_by_id(request.product_id)
        if not product:
            logger.warning(f"Inventory creation failed: Product ID {request.product_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{request.product_id}' not found",
            )

        existing = await self.inventory_crud.get_by_product_and_warehouse(
            product_id=product.id,
            warehouse_id=warehouse_id,
        )
        if existing:
            logger.warning(
                f"Inventory creation failed: Record already exists for product {product.id} at warehouse {wh_code}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inventory record for product '{product.sku}' at warehouse '{wh_code}' already exists",
            )

        new_inventory = InventoryModel(
            product_id=product.id,
            warehouse_id=warehouse_id,
            available_quantity=request.initial_available,
            reserved_quantity=0,
            damaged_quantity=0,
        )
        created = await self.inventory_crud.create_inventory(new_inventory)
        audit_service = AuditService()
        await audit_service.record_event(
            action=AuditAction.INVENTORY_CREATED,
            entity_type="INVENTORY",
            entity_id=created.id,
            warehouse_id=created.warehouse_id,
            warehouse_code=wh_code,
            user_id=current_user.id if current_user else None,
            new_state={"available_quantity": created.available_quantity},
            metadata={"product_id": created.product_id, "sku": product.sku},
        )

        return InventoryResponse(
            id=created.id,
            product_id=created.product_id,
            warehouse_id=created.warehouse_id,
            available_quantity=created.available_quantity,
            reserved_quantity=created.reserved_quantity,
            damaged_quantity=created.damaged_quantity,
            sku=product.sku,
            product_name=product.name,
            warehouse_code=wh_code,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def adjust_inventory(
        self,
        inventory_id: str,
        request: InventoryAdjustmentRequest,
        current_user: UserModel,
    ) -> InventoryResponse:
        """Adjusts available stock levels using a signed quantity delta and logs an InventoryMovement event.
        Enforces available_quantity >= 0 invariant check; raises HTTP 400 for negative stock results.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            request (InventoryAdjustmentRequest): Signed adjustment parameters.
            current_user (UserModel): Authenticated user executing cycle count adjustment.

        Returns:
            InventoryResponse: Updated inventory record details.
        """
        logger.info(
            f"Executing InventoryController.adjust_inventory for ID {inventory_id} "
            f"delta={request.quantity_delta} by user {current_user.email}"
        )
        record = await self.inventory_crud.get_by_id(inventory_id)
        if not record:
            logger.warning(f"Inventory adjustment failed: ID {inventory_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory record with ID '{inventory_id}' not found",
            )

        new_available = record.available_quantity + request.quantity_delta
        if new_available < 0:
            logger.warning(
                f"Inventory adjustment rejected: Delta {request.quantity_delta} "
                f"would reduce current available {record.available_quantity} to {new_available}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock: Adjustment of {request.quantity_delta} "
                    f"would result in negative available quantity ({new_available})"
                ),
            )

        updated = await self.inventory_crud.update_inventory(
            inventory_id=inventory_id,
            update_data={"available_quantity": new_available},
        )

        movement_log = InventoryMovementModel(
            product_id=record.product_id,
            warehouse_id=record.warehouse_id,
            movement_type="ADJUSTMENT",
            quantity=request.quantity_delta,
            reference_type="MANUAL_ADJUSTMENT",
            user_id=current_user.id,
            note=request.note,
        )
        await self.movement_crud.create_movement(movement_log)

        db = DatabaseManager.get_db()
        product = await self.product_crud.get_by_id(record.product_id)
        wh = await db["warehouses"].find_one({"_id": ObjectId(record.warehouse_id)})

        wh_code = wh["code"] if wh else None
        audit_service = AuditService()
        await audit_service.record_event(
            action=AuditAction.INVENTORY_ADJUSTED,
            entity_type="INVENTORY",
            entity_id=updated.id,
            warehouse_id=updated.warehouse_id,
            warehouse_code=wh_code,
            user_id=current_user.id,
            previous_state={"available_quantity": record.available_quantity},
            new_state={"available_quantity": updated.available_quantity},
            metadata={"quantity_delta": request.quantity_delta, "note": request.note, "product_id": record.product_id},
        )

        return InventoryResponse(
            id=updated.id,
            product_id=updated.product_id,
            warehouse_id=updated.warehouse_id,
            available_quantity=updated.available_quantity,
            reserved_quantity=updated.reserved_quantity,
            damaged_quantity=updated.damaged_quantity,
            sku=product.sku if product else None,
            product_name=product.name if product else None,
            warehouse_code=wh["code"] if wh else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    async def list_movements(self, inventory_id: str) -> List[InventoryMovementResponse]:
        """Retrieves historical InventoryMovement change logs for an inventory context.
        Raises HTTP 404 Not Found if target inventory record does not exist.

        Args:
            inventory_id (str): Target inventory ObjectId string.

        Returns:
            List[InventoryMovementResponse]: List of historical movement logs.
        """
        logger.info(f"Executing InventoryController.list_movements for {inventory_id}")
        record = await self.inventory_crud.get_by_id(inventory_id)
        if not record:
            logger.warning(f"Movements retrieval failed: Inventory ID {inventory_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory record with ID '{inventory_id}' not found",
            )

        movements = await self.movement_crud.list_movements_by_context(
            product_id=record.product_id,
            warehouse_id=record.warehouse_id,
        )
        return [
            InventoryMovementResponse(
                id=m.id,
                product_id=m.product_id,
                warehouse_id=m.warehouse_id,
                movement_type=m.movement_type,
                quantity=m.quantity,
                reference_type=m.reference_type,
                user_id=m.user_id,
                note=m.note,
                created_at=m.created_at,
            )
            for m in movements
        ]

    async def reserve_inventory(
        self,
        inventory_id: str,
        request: InventoryReservationRequest,
        current_user: UserModel,
    ) -> InventoryResponse:
        """Reserves stock using an atomic MongoDB conditional update via InventoryReservationService.
        Differentiates missing inventory (404) from insufficient stock (409). Logs a RESERVATION movement.

        Args:
            inventory_id (str): Target inventory ObjectId string.
            request (InventoryReservationRequest): Positive reservation quantity (> 0).
            current_user (UserModel): Authenticated user requesting reservation.

        Returns:
            InventoryResponse: Updated inventory state details.
        """
        logger.info(
            f"Executing InventoryController.reserve_inventory for ID {inventory_id} "
            f"requested_quantity={request.quantity} by user {current_user.email}"
        )
        # Existence lookup for 404 vs 409 classification
        record = await self.inventory_crud.get_by_id(inventory_id)
        if not record:
            logger.warning(f"Inventory reservation failed: ID {inventory_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory record with ID '{inventory_id}' not found",
            )

        updated = await self.reservation_service.reserve_item_atomic(
            inventory_id=inventory_id,
            requested_quantity=request.quantity,
            user_id=current_user.id,
            reference_type="RESERVATION",
            reference_id=None,
        )
        if not updated:
            logger.warning(
                f"Inventory reservation rejected: Insufficient stock for ID {inventory_id} "
                f"(current available={record.available_quantity}, requested={request.quantity})"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient inventory available for reservation",
            )

        db = DatabaseManager.get_db()
        product = await self.product_crud.get_by_id(updated.product_id)
        wh = await db["warehouses"].find_one({"_id": ObjectId(updated.warehouse_id)})

        return InventoryResponse(
            id=updated.id,
            product_id=updated.product_id,
            warehouse_id=updated.warehouse_id,
            available_quantity=updated.available_quantity,
            reserved_quantity=updated.reserved_quantity,
            damaged_quantity=updated.damaged_quantity,
            sku=product.sku if product else None,
            product_name=product.name if product else None,
            warehouse_code=wh["code"] if wh else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
