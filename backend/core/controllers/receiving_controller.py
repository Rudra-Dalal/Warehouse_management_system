import asyncio
import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, OperationFailure

from commons.logger import get_logger
from core.apis.schemas.requests.receiving_request import ReceivingCreateRequest
from core.apis.schemas.responses.receiving_response import (
    ReceivingItemResponse,
    ReceivingResponse,
)
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.receiving_crud import ReceivingCRUD
from core.cruds.seller_crud import SellerCRUD
from core.database.database import DatabaseManager
from core.models.inventory_movement_model import InventoryMovementModel
from core.models.receiving_model import ReceivingItemModel, ReceivingShipmentModel
from core.models.user_model import UserModel

logger = get_logger(__name__)


class ReceivingController:
    """Business logic controller orchestrating inbound inventory receiving shipments and idempotency."""

    def __init__(self):
        self.receiving_crud = ReceivingCRUD()
        self.inventory_crud = InventoryCRUD()
        self.inventory_movement_crud = InventoryMovementCRUD()
        self.product_crud = ProductCRUD()
        self.seller_crud = SellerCRUD()

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

    async def _build_receiving_response(self, shipment: ReceivingShipmentModel) -> ReceivingResponse:
        """Helper to enrich a ReceivingShipmentModel into a ReceivingResponse with product/warehouse metadata."""
        wh_doc = await self._get_warehouse_by_id(shipment.warehouse_id)
        seller = await self.seller_crud.get_by_id(shipment.seller_id)

        item_responses = []
        for item in shipment.items:
            product = await self.product_crud.get_by_id(item.product_id)
            item_responses.append(
                ReceivingItemResponse(
                    product_id=item.product_id,
                    sku=product.sku if product else None,
                    product_name=product.name if product else None,
                    quantity=item.quantity,
                )
            )

        return ReceivingResponse(
            id=shipment.id,
            receiving_reference=shipment.receiving_reference,
            warehouse_id=shipment.warehouse_id,
            warehouse_code=wh_doc["code"] if wh_doc else None,
            seller_id=shipment.seller_id,
            seller_code=seller.code if seller else None,
            status=shipment.status,
            items=item_responses,
            received_by_user_id=shipment.received_by_user_id,
            received_at=shipment.received_at,
            created_at=shipment.created_at,
        )

    async def _wait_for_received_shipment(
        self,
        receiving_reference: str,
        timeout_seconds: float = 3.0,
    ) -> Optional[ReceivingShipmentModel]:
        """Polls MongoDB for an in-flight receiving operation to reach RECEIVED status."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            shipment = await self.receiving_crud.get_by_reference(receiving_reference)
            if shipment and shipment.status == "RECEIVED":
                return shipment
            await asyncio.sleep(0.05)
        return await self.receiving_crud.get_by_reference(receiving_reference)

    async def _process_receiving_items(
        self,
        shipment: ReceivingShipmentModel,
        warehouse_id: str,
        items: List[ReceivingItemModel],
        current_user: UserModel,
        session=None,
    ) -> ReceivingShipmentModel:
        """Helper to perform atomic stock increments, log movements, and update shipment status to RECEIVED."""
        for item in items:
            await self.inventory_crud.increment_inventory_atomic(
                product_id=item.product_id,
                warehouse_id=warehouse_id,
                quantity=item.quantity,
                session=session,
            )
            await self.inventory_movement_crud.create_movement(
                movement=InventoryMovementModel(
                    product_id=item.product_id,
                    warehouse_id=warehouse_id,
                    movement_type="RECEIVING",
                    quantity=item.quantity,
                    reference_type="RECEIVING",
                    reference_id=shipment.id,
                    user_id=current_user.id,
                ),
                session=session,
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        updated_shipment = await self.receiving_crud.update_shipment_status(
            shipment_id=shipment.id,
            status="RECEIVED",
            received_at=now,
            session=session,
        )
        return updated_shipment

    async def receive_shipment(
        self,
        request: ReceivingCreateRequest,
        current_user: UserModel,
    ) -> ReceivingResponse:
        """Processes an inbound receiving shipment idempotently.

        Enforces strict single-receiving-reference uniqueness via MongoDB unique index on receiving_reference.

        Args:
            request (ReceivingCreateRequest): Inbound shipment request payload.
            current_user (UserModel): Authenticated user processing the receiving.

        Returns:
            ReceivingResponse: Receiving shipment result response.

        Raises:
            HTTPException: 404 for invalid seller, warehouse, or products; 422 for validation errors.
        """
        logger.info(
            f"Executing ReceivingController.receive_shipment for ref '{request.receiving_reference}' "
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

        # 3. Validate Products (All must exist)
        for item in request.items:
            product = await self.product_crud.get_by_id(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product ID '{item.product_id}' not found",
                )

        # 4. Fast-path check: If receiving_reference already exists and is RECEIVED -> return existing result idempotently
        existing_shipment = await self.receiving_crud.get_by_reference(request.receiving_reference)
        if existing_shipment:
            if existing_shipment.status == "RECEIVED":
                logger.info(f"Receiving reference '{request.receiving_reference}' already RECEIVED. Returning idempotent result.")
                return await self._build_receiving_response(existing_shipment)
            elif existing_shipment.status == "PROCESSING":
                completed = await self._wait_for_received_shipment(request.receiving_reference)
                if completed and completed.status == "RECEIVED":
                    return await self._build_receiving_response(completed)

        # 5. Database execution (Enforces UNIQUE receiving_reference at MongoDB layer)
        client = DatabaseManager.client
        if not client:
            raise RuntimeError("Database connection not initialized")

        shipment_model = ReceivingShipmentModel(
            receiving_reference=request.receiving_reference,
            warehouse_id=warehouse_id,
            seller_id=seller.id,
            status="PROCESSING",
            items=[ReceivingItemModel(product_id=it.product_id, quantity=it.quantity) for it in request.items],
            received_by_user_id=current_user.id,
        )

        txn_supported = True
        try:
            async with client.start_session() as session:
                try:
                    await session.start_transaction()

                    try:
                        shipment = await self.receiving_crud.create_receiving_shipment(shipment_model, session=session)
                    except DuplicateKeyError:
                        await session.abort_transaction()
                        completed = await self._wait_for_received_shipment(request.receiving_reference)
                        if completed and completed.status == "RECEIVED":
                            return await self._build_receiving_response(completed)
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Receiving reference '{request.receiving_reference}' is currently being processed",
                        )

                    updated_shipment = await self._process_receiving_items(
                        shipment=shipment,
                        warehouse_id=warehouse_id,
                        items=shipment_model.items,
                        current_user=current_user,
                        session=session,
                    )

                    await session.commit_transaction()
                    logger.info(f"Successfully processed receiving shipment '{request.receiving_reference}' (transactional)")
                    return await self._build_receiving_response(updated_shipment)

                except OperationFailure as op_err:
                    if op_err.code == 20 or "Transaction numbers" in str(op_err):
                        txn_supported = False
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                    else:
                        try:
                            await session.abort_transaction()
                        except Exception:
                            pass
                        raise op_err
                except Exception as txn_err:
                    try:
                        await session.abort_transaction()
                    except Exception:
                        pass
                    raise txn_err
        except HTTPException:
            raise
        except Exception as err:
            if txn_supported and not isinstance(err, OperationFailure):
                logger.error(f"Transaction error in receive_shipment: {err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Receiving transaction failed: {str(err)}",
                )

        # Fallback for standalone MongoDB deployment (Atomicity protected by UNIQUE receiving_reference index + atomic $inc)
        if not txn_supported:
            try:
                shipment = await self.receiving_crud.create_receiving_shipment(shipment_model)
            except DuplicateKeyError:
                completed = await self._wait_for_received_shipment(request.receiving_reference)
                if completed and completed.status == "RECEIVED":
                    return await self._build_receiving_response(completed)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Receiving reference '{request.receiving_reference}' is currently being processed",
                )

            updated_shipment = await self._process_receiving_items(
                shipment=shipment,
                warehouse_id=warehouse_id,
                items=shipment_model.items,
                current_user=current_user,
                session=None,
            )
            logger.info(f"Successfully processed receiving shipment '{request.receiving_reference}' (standalone atomic)")
            return await self._build_receiving_response(updated_shipment)

    async def get_receiving_by_id(self, shipment_id: str) -> ReceivingResponse:
        """Retrieves receiving shipment details by ObjectId string.

        Args:
            shipment_id (str): Target receiving shipment ObjectId string.

        Returns:
            ReceivingResponse: Enriched receiving response.
        """
        shipment = await self.receiving_crud.get_by_id(shipment_id)
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receiving shipment ID '{shipment_id}' not found",
            )
        return await self._build_receiving_response(shipment)

    async def list_receivings(
        self,
        warehouse_code: Optional[str] = None,
        seller_id: Optional[str] = None,
    ) -> List[ReceivingResponse]:
        """Lists receiving shipments with optional filters."""
        warehouse_id = None
        if warehouse_code:
            wh_doc = await self._get_warehouse_by_code(warehouse_code)
            if wh_doc:
                warehouse_id = str(wh_doc["_id"])
            else:
                return []

        shipments = await self.receiving_crud.list_receiving_shipments(
            warehouse_id=warehouse_id,
            seller_id=seller_id,
        )
        return [await self._build_receiving_response(s) for s in shipments]
