from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from commons.auth import require_permission
from core.apis.schemas.requests.fulfillment_request import (
    FulfillmentCreateRequest,
    PackFulfillmentRequest,
    PickFulfillmentRequest,
    ShipFulfillmentRequest,
)
from core.apis.schemas.responses.fulfillment_response import FulfillmentResponse
from core.controllers.fulfillment_controller import FulfillmentController
from core.models.user_model import UserModel

router = APIRouter(prefix="/v1/fulfillment", tags=["Fulfillment Execution"])
controller = FulfillmentController()


@router.post(
    "",
    response_model=FulfillmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create fulfillment task for a confirmed order",
)
async def create_fulfillment(
    request: FulfillmentCreateRequest,
    current_user: UserModel = Depends(require_permission("fulfillment.pick")),
):
    """Creates an operational fulfillment record for a CONFIRMED order.

    Idempotently returns existing record if already created for the order.
    """
    return await controller.create_fulfillment(request, current_user)


@router.get(
    "",
    response_model=List[FulfillmentResponse],
    summary="List fulfillment records with optional filters",
)
async def list_fulfillments(
    warehouse_code: Optional[str] = Query(None, description="Filter by warehouse code (RENO/COLUMBUS)"),
    status: Optional[str] = Query(None, description="Filter by status (READY_TO_PICK, PICKED, PACKED, SHIPPED)"),
    current_user: UserModel = Depends(require_permission("fulfillment.read")),
):
    """Lists fulfillment execution records with optional warehouse and status filtering."""
    return await controller.list_fulfillments(warehouse_code=warehouse_code, status_filter=status)


@router.get(
    "/{fulfillment_id}",
    response_model=FulfillmentResponse,
    summary="Get fulfillment record by ID",
)
async def get_fulfillment_by_id(
    fulfillment_id: str,
    current_user: UserModel = Depends(require_permission("fulfillment.read")),
):
    """Retrieves a fulfillment execution record by ObjectId string."""
    return await controller.get_fulfillment_by_id(fulfillment_id)


@router.post(
    "/{fulfillment_id}/pick",
    response_model=FulfillmentResponse,
    summary="Execute picking for a fulfillment task",
)
async def pick_fulfillment(
    fulfillment_id: str,
    request: PickFulfillmentRequest,
    current_user: UserModel = Depends(require_permission("fulfillment.pick")),
):
    """Executes picking operation for a READY_TO_PICK fulfillment inside a MongoDB transaction.

    Consumes inventory reservation (decrements reserved_quantity), logs PICK movement, and updates status to PICKED.
    """
    return await controller.pick_fulfillment(fulfillment_id, request, current_user)


@router.post(
    "/{fulfillment_id}/pack",
    response_model=FulfillmentResponse,
    summary="Execute packing for a picked fulfillment task",
)
async def pack_fulfillment(
    fulfillment_id: str,
    request: PackFulfillmentRequest,
    current_user: UserModel = Depends(require_permission("fulfillment.pack")),
):
    """Executes packing operation for a PICKED fulfillment, updating status to PACKED."""
    return await controller.pack_fulfillment(fulfillment_id, request, current_user)


@router.post(
    "/{fulfillment_id}/ship",
    response_model=FulfillmentResponse,
    summary="Execute shipping for a packed fulfillment task",
)
async def ship_fulfillment(
    fulfillment_id: str,
    request: ShipFulfillmentRequest,
    current_user: UserModel = Depends(require_permission("fulfillment.ship")),
):
    """Executes shipping operation for a PACKED fulfillment inside a transaction, updating fulfillment and order to SHIPPED."""
    return await controller.ship_fulfillment(fulfillment_id, request, current_user)
