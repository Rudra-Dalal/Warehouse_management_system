import asyncio
import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, OperationFailure

from commons.logger import get_logger
from core.apis.schemas.requests.fulfillment_request import (
    FulfillmentCreateRequest,
    PackFulfillmentRequest,
    PickFulfillmentRequest,
    ShipFulfillmentRequest,
)
from core.apis.schemas.responses.fulfillment_response import (
    FulfillmentItemResponse,
    FulfillmentResponse,
)
from core.cruds.fulfillment_crud import FulfillmentCRUD
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.product_crud import ProductCRUD
from core.database.database import DatabaseManager
from core.models.fulfillment_model import (
    FulfillmentItemModel,
    FulfillmentModel,
    FulfillmentStatus,
)
from core.models.inventory_movement_model import InventoryMovementModel
from core.models.user_model import UserModel
from core.services.fulfillment_service import FulfillmentService

logger = get_logger(__name__)


class FulfillmentController:
    """Business logic controller orchestrating order fulfillment execution (Pick -> Pack -> Ship)."""

    def __init__(self):
        self.fulfillment_crud = FulfillmentCRUD()
        self.order_crud = OrderCRUD()
        self.inventory_crud = InventoryCRUD()
        self.movement_crud = InventoryMovementCRUD()
        self.product_crud = ProductCRUD()
        self.fulfillment_service = FulfillmentService()

    @property
    def warehouses_collection(self):
        return DatabaseManager.get_db()["warehouses"]

    async def _get_warehouse_by_code(self, code: str):
        if not code:
            return None
        return await self.warehouses_collection.find_one({"code": code.upper().strip()})

    async def _get_warehouse_by_id(self, warehouse_id: str):
        if not ObjectId.is_valid(warehouse_id):
            return None
        return await self.warehouses_collection.find_one({"_id": ObjectId(warehouse_id)})

    async def _build_fulfillment_response(self, fulfillment: FulfillmentModel) -> FulfillmentResponse:
        """Enriches a FulfillmentModel into a FulfillmentResponse with product and warehouse metadata."""
        wh_doc = await self._get_warehouse_by_id(fulfillment.warehouse_id)

        item_responses = []
        for item in fulfillment.items:
            product = await self.product_crud.get_by_id(item.product_id)
            item_responses.append(
                FulfillmentItemResponse(
                    product_id=item.product_id,
                    sku=product.sku if product else None,
                    product_name=product.name if product else None,
                    quantity=item.quantity,
                    picked_quantity=item.picked_quantity,
                    packed_quantity=item.packed_quantity,
                )
            )

        return FulfillmentResponse(
            id=fulfillment.id,
            order_id=fulfillment.order_id,
            order_number=fulfillment.order_number,
            warehouse_id=fulfillment.warehouse_id,
            warehouse_code=wh_doc["code"] if wh_doc else None,
            status=fulfillment.status.value if isinstance(fulfillment.status, FulfillmentStatus) else str(fulfillment.status),
            items=item_responses,
            picked_at=fulfillment.picked_at,
            picked_by_user_id=fulfillment.picked_by_user_id,
            packed_at=fulfillment.packed_at,
            packed_by_user_id=fulfillment.packed_by_user_id,
            shipped_at=fulfillment.shipped_at,
            shipped_by_user_id=fulfillment.shipped_by_user_id,
            created_at=fulfillment.created_at,
            updated_at=fulfillment.updated_at,
        )

    async def create_fulfillment(
        self,
        request: FulfillmentCreateRequest,
        current_user: UserModel,
    ) -> FulfillmentResponse:
        """Creates a fulfillment execution record for a CONFIRMED order.

        Enforces ONE fulfillment per order via database unique index. Returns existing fulfillment idempotently.
        """
        logger.info(f"Executing FulfillmentController.create_fulfillment for order_id '{request.order_id}'")

        # 1. Validate Order
        order = await self.order_crud.get_by_id(request.order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order ID '{request.order_id}' not found",
            )

        # 2. Precondition: Order status MUST be CONFIRMED
        if order.status != "CONFIRMED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fulfillment cannot be created for order in status '{order.status}'. Order must be CONFIRMED.",
            )

        # 3. Idempotency Check: Return existing fulfillment if already created
        existing = await self.fulfillment_crud.get_by_order_id(order.id)
        if existing:
            logger.info(f"Fulfillment for order ID '{order.id}' already exists. Returning idempotent result.")
            return await self._build_fulfillment_response(existing)

        # 4. Construct FulfillmentModel inheriting order metadata and line items
        fulfillment_items = [
            FulfillmentItemModel(
                product_id=it.product_id,
                quantity=it.quantity,
                picked_quantity=0,
                packed_quantity=0,
            )
            for it in order.items
        ]

        fulfillment_model = FulfillmentModel(
            order_id=order.id,
            order_number=order.order_number,
            warehouse_id=order.warehouse_id,
            status=FulfillmentStatus.READY_TO_PICK,
            items=fulfillment_items,
        )

        try:
            created = await self.fulfillment_crud.create_fulfillment(fulfillment_model)
            logger.info(f"Successfully created fulfillment '{created.id}' for order '{order.order_number}'")
            return await self._build_fulfillment_response(created)
        except DuplicateKeyError:
            logger.info(f"Duplicate key detected for fulfillment order_id '{order.id}'. Returning existing record.")
            existing_after_dup = await self.fulfillment_crud.get_by_order_id(order.id)
            if existing_after_dup:
                return await self._build_fulfillment_response(existing_after_dup)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fulfillment for order ID '{order.id}' is currently being created",
            )

    async def get_fulfillment_by_id(self, fulfillment_id: str) -> FulfillmentResponse:
        """Retrieves a fulfillment execution record by ObjectId string."""
        fulfillment = await self.fulfillment_crud.get_by_id(fulfillment_id)
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment ID '{fulfillment_id}' not found",
            )
        return await self._build_fulfillment_response(fulfillment)

    async def list_fulfillments(
        self,
        warehouse_code: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[FulfillmentResponse]:
        """Lists fulfillment records with optional filters."""
        warehouse_id = None
        if warehouse_code:
            wh_doc = await self._get_warehouse_by_code(warehouse_code)
            if wh_doc:
                warehouse_id = str(wh_doc["_id"])
            else:
                return []

        fulfillments = await self.fulfillment_crud.list_fulfillments(
            warehouse_id=warehouse_id,
            status=status_filter,
        )
        return [await self._build_fulfillment_response(f) for f in fulfillments]

    async def pick_fulfillment(
        self,
        fulfillment_id: str,
        request: PickFulfillmentRequest,
        current_user: UserModel,
    ) -> FulfillmentResponse:
        """Executes picking operation for a READY_TO_PICK fulfillment inside a MongoDB transaction.

        Consumes inventory reservation (decrements reserved_quantity without modifying available_quantity),
        logs PICK movements, and transitions status to PICKED.
        """
        logger.info(f"Executing FulfillmentController.pick_fulfillment for ID '{fulfillment_id}' by user {current_user.id}")

        # 1. Validate Fulfillment exists
        fulfillment = await self.fulfillment_crud.get_by_id(fulfillment_id)
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment ID '{fulfillment_id}' not found",
            )

        # 2. Idempotency & State Checks
        if fulfillment.status == FulfillmentStatus.PICKED:
            # Check if requested pick payload matches
            try:
                pick_items_dict = [it.model_dump() for it in request.items]
                self.fulfillment_service.validate_and_build_pick_items(fulfillment, pick_items_dict)
                logger.info(f"Fulfillment '{fulfillment_id}' already PICKED with identical items. Returning idempotent response.")
                return await self._build_fulfillment_response(fulfillment)
            except ValueError as err:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Fulfillment '{fulfillment_id}' is already PICKED: {err}",
                )

        if fulfillment.status in [FulfillmentStatus.PACKED, FulfillmentStatus.SHIPPED]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot pick fulfillment in state '{fulfillment.status.value}'. Transition rejected.",
            )

        # 3. Validate state transition rules
        try:
            self.fulfillment_service.validate_transition(fulfillment.status, FulfillmentStatus.PICKED)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )

        # 4. Validate pick item quantities
        try:
            pick_items_dict = [it.model_dump() for it in request.items]
            updated_items = self.fulfillment_service.validate_and_build_pick_items(fulfillment, pick_items_dict)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err),
            )

        # 5. Transactional Execution
        client = DatabaseManager.client
        if not client:
            raise RuntimeError("Database connection not initialized")

        if DatabaseManager.is_transaction_supported():
            max_retries = 5
            for attempt in range(max_retries):
                async with client.start_session() as session:
                    try:
                        await session.start_transaction()

                        # Consume reservation & log PICK movement for each item
                        for item in updated_items:
                            inv = await self.inventory_crud.get_by_product_and_warehouse(
                                product_id=item.product_id,
                                warehouse_id=fulfillment.warehouse_id,
                                session=session,
                            )
                            if not inv:
                                await session.abort_transaction()
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Inventory record not found for product ID '{item.product_id}'",
                                )

                            consumed_inv = await self.inventory_crud.consume_reservation_atomic(
                                inventory_id=inv.id,
                                picked_quantity=item.picked_quantity,
                                session=session,
                            )
                            if not consumed_inv:
                                await session.abort_transaction()
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Insufficient reserved inventory for product ID '{item.product_id}'",
                                )

                            # Log PICK inventory movement
                            movement = InventoryMovementModel(
                                product_id=item.product_id,
                                warehouse_id=fulfillment.warehouse_id,
                                movement_type="PICK",
                                quantity=-item.picked_quantity,
                                reference_type="FULFILLMENT",
                                reference_id=fulfillment.id,
                                user_id=current_user.id,
                            )
                            await self.movement_crud.create_movement(movement, session=session)

                        picked_at = datetime.datetime.now(datetime.timezone.utc)
                        updated_fulfillment = await self.fulfillment_crud.update_pick_progress(
                            fulfillment_id=fulfillment.id,
                            items=updated_items,
                            picked_by_user_id=current_user.id,
                            picked_at=picked_at,
                            session=session,
                        )

                        await session.commit_transaction()
                        logger.info(f"Successfully picked fulfillment '{fulfillment.id}' (transactional)")
                        return await self._build_fulfillment_response(updated_fulfillment)

                    except OperationFailure as op_err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        is_transient = op_err.has_error_label("TransientTransactionError") or op_err.code == 112
                        if is_transient and attempt < max_retries - 1:
                            logger.warning(f"Transient transaction WriteConflict on pick attempt {attempt+1}. Retrying...")
                            await asyncio.sleep(0.02 * (2 ** attempt))
                            continue
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Concurrent pick conflict for fulfillment '{fulfillment_id}'",
                        )
                    except Exception as err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        if isinstance(err, HTTPException):
                            raise err
                        logger.error(f"Transaction error in pick_fulfillment: {err}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Pick transaction failed: {str(err)}",
                        )

        # Standalone MongoDB deployment fallback
        for item in updated_items:
            inv = await self.inventory_crud.get_by_product_and_warehouse(
                product_id=item.product_id,
                warehouse_id=fulfillment.warehouse_id,
                session=None,
            )
            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inventory record not found for product ID '{item.product_id}'",
                )

            consumed_inv = await self.inventory_crud.consume_reservation_atomic(
                inventory_id=inv.id,
                picked_quantity=item.picked_quantity,
                session=None,
            )
            if not consumed_inv:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient reserved inventory for product ID '{item.product_id}'",
                )

            movement = InventoryMovementModel(
                product_id=item.product_id,
                warehouse_id=fulfillment.warehouse_id,
                movement_type="PICK",
                quantity=-item.picked_quantity,
                reference_type="FULFILLMENT",
                reference_id=fulfillment.id,
                user_id=current_user.id,
            )
            await self.movement_crud.create_movement(movement, session=None)

        picked_at = datetime.datetime.now(datetime.timezone.utc)
        updated_fulfillment = await self.fulfillment_crud.update_pick_progress(
            fulfillment_id=fulfillment.id,
            items=updated_items,
            picked_by_user_id=current_user.id,
            picked_at=picked_at,
            session=None,
        )
        logger.info(f"Successfully picked fulfillment '{fulfillment.id}' (non-transactional fallback)")
        return await self._build_fulfillment_response(updated_fulfillment)

    async def pack_fulfillment(
        self,
        fulfillment_id: str,
        request: PackFulfillmentRequest,
        current_user: UserModel,
    ) -> FulfillmentResponse:
        """Executes packing operation for a PICKED fulfillment.

        Transitions status to PACKED. Does not modify inventory stock.
        """
        logger.info(f"Executing FulfillmentController.pack_fulfillment for ID '{fulfillment_id}' by user {current_user.id}")

        # 1. Validate Fulfillment exists
        fulfillment = await self.fulfillment_crud.get_by_id(fulfillment_id)
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment ID '{fulfillment_id}' not found",
            )

        # 2. Idempotency Check: Return existing if already PACKED or SHIPPED
        if fulfillment.status in [FulfillmentStatus.PACKED, FulfillmentStatus.SHIPPED]:
            logger.info(f"Fulfillment '{fulfillment_id}' is already '{fulfillment.status.value}'. Returning idempotent response.")
            return await self._build_fulfillment_response(fulfillment)

        # 3. Validate State Transition rules (MUST be PICKED -> PACKED)
        try:
            self.fulfillment_service.validate_transition(fulfillment.status, FulfillmentStatus.PACKED)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )

        # 4. Verify all items are fully picked
        packed_items = []
        for item in fulfillment.items:
            if item.picked_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Item '{item.product_id}' is not fully picked ({item.picked_quantity}/{item.quantity}). Cannot pack.",
                )
            packed_items.append(
                FulfillmentItemModel(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    picked_quantity=item.picked_quantity,
                    packed_quantity=item.picked_quantity,
                )
            )

        packed_at = datetime.datetime.now(datetime.timezone.utc)
        updated = await self.fulfillment_crud.update_pack_progress(
            fulfillment_id=fulfillment.id,
            items=packed_items,
            packed_by_user_id=current_user.id,
            packed_at=packed_at,
        )

        logger.info(f"Successfully packed fulfillment '{fulfillment.id}'")
        return await self._build_fulfillment_response(updated)

    async def ship_fulfillment(
        self,
        fulfillment_id: str,
        request: ShipFulfillmentRequest,
        current_user: UserModel,
    ) -> FulfillmentResponse:
        """Executes shipping operation for a PACKED fulfillment inside a single MongoDB transaction.

        Transitions fulfillment status to SHIPPED and order status to SHIPPED atomically.
        """
        logger.info(f"Executing FulfillmentController.ship_fulfillment for ID '{fulfillment_id}' by user {current_user.id}")

        # 1. Validate Fulfillment exists
        fulfillment = await self.fulfillment_crud.get_by_id(fulfillment_id)
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment ID '{fulfillment_id}' not found",
            )

        # 2. Idempotency Check: Return existing if already SHIPPED
        if fulfillment.status == FulfillmentStatus.SHIPPED:
            logger.info(f"Fulfillment '{fulfillment_id}' is already SHIPPED. Returning idempotent response.")
            return await self._build_fulfillment_response(fulfillment)

        # 3. Validate State Transition rules (MUST be PACKED -> SHIPPED)
        try:
            self.fulfillment_service.validate_transition(fulfillment.status, FulfillmentStatus.SHIPPED)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )

        # 4. Transactional Execution to update Fulfillment status to SHIPPED and Order status to SHIPPED
        client = DatabaseManager.client
        if not client:
            raise RuntimeError("Database connection not initialized")

        if DatabaseManager.is_transaction_supported():
            max_retries = 5
            for attempt in range(max_retries):
                async with client.start_session() as session:
                    try:
                        await session.start_transaction()

                        shipped_at = datetime.datetime.now(datetime.timezone.utc)
                        updated_fulfillment = await self.fulfillment_crud.update_shipping_state(
                            fulfillment_id=fulfillment.id,
                            shipped_by_user_id=current_user.id,
                            shipped_at=shipped_at,
                            session=session,
                        )

                        # Update associated Order status to SHIPPED
                        await self.order_crud.update_order_status(
                            order_id=fulfillment.order_id,
                            status="SHIPPED",
                            session=session,
                        )

                        await session.commit_transaction()
                        logger.info(f"Successfully shipped fulfillment '{fulfillment.id}' and order '{fulfillment.order_id}' (transactional)")
                        return await self._build_fulfillment_response(updated_fulfillment)

                    except OperationFailure as op_err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        is_transient = op_err.has_error_label("TransientTransactionError") or op_err.code == 112
                        if is_transient and attempt < max_retries - 1:
                            logger.warning(f"Transient transaction WriteConflict on ship attempt {attempt+1}. Retrying...")
                            await asyncio.sleep(0.02 * (2 ** attempt))
                            continue
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Concurrent shipping conflict for fulfillment '{fulfillment_id}'",
                        )
                    except Exception as err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        if isinstance(err, HTTPException):
                            raise err
                        logger.error(f"Transaction error in ship_fulfillment: {err}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Ship transaction failed: {str(err)}",
                        )

        # Standalone MongoDB deployment fallback
        shipped_at = datetime.datetime.now(datetime.timezone.utc)
        updated_fulfillment = await self.fulfillment_crud.update_shipping_state(
            fulfillment_id=fulfillment.id,
            shipped_by_user_id=current_user.id,
            shipped_at=shipped_at,
            session=None,
        )
        await self.order_crud.update_order_status(
            order_id=fulfillment.order_id,
            status="SHIPPED",
            session=None,
        )
        logger.info(f"Successfully shipped fulfillment '{fulfillment.id}' and order '{fulfillment.order_id}' (non-transactional fallback)")
        return await self._build_fulfillment_response(updated_fulfillment)
