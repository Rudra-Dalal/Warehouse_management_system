from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from commons.auth import get_current_user, require_permission, authorize_warehouse
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
    await authorize_warehouse(current_user, request.warehouse_code)
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
    if warehouse_code:
        await authorize_warehouse(current_user, warehouse_code)

    results = await receiving_controller.list_receivings(
        warehouse_code=warehouse_code, seller_id=seller_id
    )

    if not warehouse_code:
        from core.cruds.role_crud import RoleCRUD
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != "ADMIN":
            results = [r for r in results if r.warehouse_code in current_user.assigned_warehouse_ids]

    return results


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
    result = await receiving_controller.get_receiving_by_id(receiving_id)
    await authorize_warehouse(current_user, result.warehouse_code)
    return result
