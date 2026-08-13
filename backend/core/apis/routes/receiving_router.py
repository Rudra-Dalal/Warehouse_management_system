from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from commons.auth import get_current_user, require_permission
from core.apis.schemas.requests.receiving_request import ReceivingCreateRequest
from core.apis.schemas.responses.receiving_response import ReceivingResponse
from core.controllers.receiving_controller import ReceivingController
from core.models.user_model import UserModel

router = APIRouter(prefix="/v1/receiving", tags=["Receiving"])
receiving_controller = ReceivingController()


@router.post(
    "",
    response_model=ReceivingResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive inbound inventory shipment (Idempotent)",
    description="Processes inbound inventory receiving shipment. Strictly idempotent via receiving_reference.",
)
async def receive_shipment(
    request: ReceivingCreateRequest,
    current_user: UserModel = Depends(require_permission("inventory.receive")),
) -> ReceivingResponse:
    """Processes an inbound receiving shipment idempotently with transactional consistency."""
    return await receiving_controller.receive_shipment(request, current_user)


@router.get(
    "",
    response_model=List[ReceivingResponse],
    summary="List receiving shipments",
    description="Lists receiving shipments filtered by warehouse code or seller ID.",
)
async def list_receivings(
    warehouse_code: Optional[str] = Query(None, description="Optional warehouse code filter (RENO/COLUMBUS)"),
    seller_id: Optional[str] = Query(None, description="Optional seller ObjectId filter"),
    current_user: UserModel = Depends(require_permission("inventory.read")),
) -> List[ReceivingResponse]:
    """Lists receiving shipments filtered by warehouse code or seller ID."""
    return await receiving_controller.list_receivings(
        warehouse_code=warehouse_code, seller_id=seller_id
    )


@router.get(
    "/{receiving_id}",
    response_model=ReceivingResponse,
    summary="Get receiving shipment by ID",
    description="Retrieves details for a specific receiving shipment by string ObjectId.",
)
async def get_receiving_by_id(
    receiving_id: str,
    current_user: UserModel = Depends(require_permission("inventory.read")),
) -> ReceivingResponse:
    """Retrieves details for a specific receiving shipment by string ObjectId."""
    return await receiving_controller.get_receiving_by_id(receiving_id)
