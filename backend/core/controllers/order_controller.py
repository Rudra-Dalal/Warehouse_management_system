import asyncio
import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, OperationFailure

from commons.logger import get_logger
from core.apis.schemas.requests.order_request import OrderCreateRequest
from core.apis.schemas.responses.order_response import (
    OrderItemResponse,
    OrderResponse,
)
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.seller_crud import SellerCRUD
from core.database.database import DatabaseManager
from core.models.order_model import OrderItemModel, OrderModel
from core.models.user_model import UserModel
from core.services.inventory_reservation_service import InventoryReservationService

logger = get_logger(__name__)


class OrderController:
    """Business logic controller orchestrating customer orders and inventory reservation integration."""

    def __init__(self):
        self.order_crud = OrderCRUD()
        self.inventory_crud = InventoryCRUD()
        self.product_crud = ProductCRUD()
        self.seller_crud = SellerCRUD()
        self.reservation_service = InventoryReservationService()

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

    async def _build_order_response(self, order: OrderModel) -> OrderResponse:
        """Enriches an OrderModel into an OrderResponse with product, seller, and warehouse metadata."""
        wh_doc = await self._get_warehouse_by_id(order.warehouse_id)
        seller = await self.seller_crud.get_by_id(order.seller_id)

        item_responses = []
        for item in order.items:
            product = await self.product_crud.get_by_id(item.product_id)
            item_responses.append(
                OrderItemResponse(
                    product_id=item.product_id,
                    sku=product.sku if product else None,
                    product_name=product.name if product else None,
                    quantity=item.quantity,
                )
            )

        return OrderResponse(
            id=order.id,
            order_number=order.order_number,
            seller_id=order.seller_id,
            seller_code=seller.code if seller else None,
            warehouse_id=order.warehouse_id,
            warehouse_code=wh_doc["code"] if wh_doc else None,
            status=order.status,
            items=item_responses,
            created_by_user_id=order.created_by_user_id,
            created_at=order.created_at,
            confirmed_at=order.confirmed_at,
        )

    async def create_and_confirm_order(
        self,
        request: OrderCreateRequest,
        current_user: UserModel,
    ) -> OrderResponse:
        """Validates an inbound order, resolves inventory, performs multi-item atomic reservation,
        and creates a confirmed order inside a single MongoDB multi-document transaction.

        Args:
            request (OrderCreateRequest): Order request payload.
            current_user (UserModel): Authenticated user processing the order.

        Returns:
            OrderResponse: Confirmed order response.

        Raises:
            HTTPException: 404 for invalid seller, warehouse, product, or missing inventory;
                           409 for insufficient stock or duplicate orders;
                           500 for missing transaction support.
        """
        logger.info(
            f"Executing OrderController.create_and_confirm_order for order_number '{request.order_number}' "
            f"by user {current_user.id}"
        )

        # 1. Validate Warehouse
        wh_doc = await self._get_warehouse_by_code(request.warehouse_code)
        if not wh_doc or not wh_doc.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse code '{request.warehouse_code}' not found or inactive",
            )
        warehouse_id = str(wh_doc["_id"])

        # 2. Validate Seller
        seller = await self.seller_crud.get_by_id(request.seller_id)
        if not seller or not seller.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller ID '{request.seller_id}' not found or inactive",
            )

        # 3. Validate ALL Products before changing inventory
        for item in request.items:
            product = await self.product_crud.get_by_id(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product ID '{item.product_id}' not found",
                )

        # 4. Fast-path check for Order Idempotency
        existing_order = await self.order_crud.get_by_order_number(request.order_number)
        if existing_order:
            if existing_order.status == "CONFIRMED":
                logger.info(
                    f"Order number '{request.order_number}' is already CONFIRMED. Returning idempotent result."
                )
                return await self._build_order_response(existing_order)

        # 5. Resolve Inventory records for all line items
        reservation_items = []
        for item in request.items:
            inv = await self.inventory_crud.get_by_product_and_warehouse(
                product_id=item.product_id,
                warehouse_id=warehouse_id,
            )
            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inventory record not found for product ID '{item.product_id}' at warehouse '{request.warehouse_code}'",
                )
            reservation_items.append({"inventory_id": inv.id, "quantity": item.quantity})

        # Pre-assign Order ObjectId string so reference_id can be passed to reservation movements
        order_id = str(ObjectId())
        now = datetime.datetime.now(datetime.timezone.utc)
        order_model = OrderModel(
            id=order_id,
            order_number=request.order_number.strip(),
            seller_id=seller.id,
            warehouse_id=warehouse_id,
            status="CONFIRMED",
            items=[OrderItemModel(product_id=it.product_id, quantity=it.quantity) for it in request.items],
            created_by_user_id=current_user.id,
            confirmed_at=now,
        )

        client = DatabaseManager.client
        if not client:
            raise RuntimeError("Database connection not initialized")

        if DatabaseManager.is_transaction_supported():
            max_retries = 5
            for attempt in range(max_retries):
                async with client.start_session() as session:
                    try:
                        await session.start_transaction()

                        # 6. Reserve ALL inventory and log movements inside transaction session
                        try:
                            await self.reservation_service.reserve_multi_items_atomic(
                                items=reservation_items,
                                user_id=current_user.id,
                                reference_type="ORDER",
                                reference_id=order_id,
                                session=session,
                            )
                        except ValueError as val_err:
                            await session.abort_transaction()
                            logger.warning(f"Order reservation failed for '{request.order_number}': {val_err}")
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Insufficient inventory available to reserve order '{request.order_number}'",
                            )

                        # 7. Persist Confirmed Order Document inside transaction session
                        try:
                            confirmed_order = await self.order_crud.create_order(order_model, session=session)
                        except DuplicateKeyError:
                            await session.abort_transaction()
                            logger.info(f"Duplicate key detected for order_number '{request.order_number}'. Returning existing order.")
                            existing = await self.order_crud.get_by_order_number(request.order_number)
                            if existing:
                                return await self._build_order_response(existing)
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Order number '{request.order_number}' is currently being processed",
                            )

                        await session.commit_transaction()
                        logger.info(f"Successfully created and confirmed order '{request.order_number}' (ID: {confirmed_order.id}) [transactional]")
                        return await self._build_order_response(confirmed_order)

                    except OperationFailure as op_err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass

                        # Targeted retry ONLY for TransientTransactionError / WriteConflict (code 112)
                        is_transient = op_err.has_error_label("TransientTransactionError") or op_err.code == 112
                        if is_transient and attempt < max_retries - 1:
                            logger.warning(
                                f"Transient transaction WriteConflict for '{request.order_number}' on attempt {attempt+1}. Retrying..."
                            )
                            await asyncio.sleep(0.02 * (2 ** attempt))
                            continue

                        logger.warning(f"Transaction conflict/failure for '{request.order_number}': {op_err}")
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Concurrent inventory reservation conflict for order '{request.order_number}'",
                        )
                    except Exception as err:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        if isinstance(err, HTTPException):
                            raise err
                        logger.error(f"Transaction error in create_and_confirm_order: {err}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Order transaction failed",
                        )

        # Standalone MongoDB deployment fallback
        try:
            await self.reservation_service.reserve_multi_items_atomic(
                items=reservation_items,
                user_id=current_user.id,
                reference_type="ORDER",
                reference_id=order_id,
                session=None,
            )
        except ValueError as val_err:
            logger.warning(f"Order reservation failed for '{request.order_number}': {val_err}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient inventory available to reserve order '{request.order_number}'",
            )
        except Exception as err:
            logger.error(f"Error during order reservation for '{request.order_number}': {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Order reservation failed: {str(err)}",
            )

        try:
            confirmed_order = await self.order_crud.create_order(order_model, session=None)
        except DuplicateKeyError:
            logger.info(f"Duplicate key detected for order_number '{request.order_number}'. Returning existing order.")
            # Unreserve duplicate stock reservations made in standalone fallback
            for item in request.items:
                inv = await self.inventory_crud.get_by_product_and_warehouse(
                    product_id=item.product_id,
                    warehouse_id=warehouse_id,
                )
                if inv:
                    await self.inventory_crud.unreserve_inventory_atomic(
                        inventory_id=inv.id,
                        quantity=item.quantity,
                    )
            await DatabaseManager.get_db()["inventory_movements"].delete_many(
                {"reference_type": "ORDER", "reference_id": order_id}
            )

            existing = await self.order_crud.get_by_order_number(request.order_number)
            if existing:
                return await self._build_order_response(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order number '{request.order_number}' is currently being processed",
            )
        except Exception as err:
            logger.error(f"Order persistence failed for '{request.order_number}', rolling back reservations: {err}")
            for item in request.items:
                inv = await self.inventory_crud.get_by_product_and_warehouse(
                    product_id=item.product_id,
                    warehouse_id=warehouse_id,
                )
                if inv:
                    await self.inventory_crud.unreserve_inventory_atomic(
                        inventory_id=inv.id,
                        quantity=item.quantity,
                    )
            # Delete movement logs recorded for this order ID during standalone fallback
            await DatabaseManager.get_db()["inventory_movements"].delete_many(
                {"reference_type": "ORDER", "reference_id": order_id}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Order persistence failed: {str(err)}",
            )

        logger.info(f"Successfully created and confirmed order '{request.order_number}' (ID: {confirmed_order.id}) [non-transactional fallback]")
        return await self._build_order_response(confirmed_order)

    async def get_order_by_id(self, order_id: str) -> OrderResponse:
        """Retrieves order details by ObjectId string.

        Args:
            order_id (str): Target order ObjectId string.

        Returns:
            OrderResponse: Enriched order response.
        """
        order = await self.order_crud.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order ID '{order_id}' not found",
            )
        return await self._build_order_response(order)

    async def list_orders(
        self,
        warehouse_code: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[OrderResponse]:
        """Lists orders with optional filters."""
        warehouse_id = None
        if warehouse_code:
            wh_doc = await self._get_warehouse_by_code(warehouse_code)
            if wh_doc:
                warehouse_id = str(wh_doc["_id"])
            else:
                return []

        orders = await self.order_crud.list_orders(
            warehouse_id=warehouse_id,
            seller_id=seller_id,
            status=status,
        )
        return [await self._build_order_response(o) for o in orders]
