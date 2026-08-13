from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from commons.auth import get_current_user, require_permission
from commons.logger import get_logger
from core.apis.schemas.requests.order_request import OrderCreateRequest
from core.apis.schemas.responses.order_response import OrderResponse
from core.controllers.order_controller import OrderController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/orders", tags=["Orders"])
order_controller = OrderController()


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("orders.confirm"))],
    summary="Create and confirm customer order",
    description=(
        "Creates a customer order, validates seller/warehouse/products, and atomically reserves inventory "
        "across all line items under all-or-nothing semantics. Enforces unique order_number idempotency."
    ),
)
async def create_order(
    request: OrderCreateRequest,
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    logger.info(f"POST /v1/orders received from user {current_user.id} for order '{request.order_number}'")
    return await order_controller.create_and_confirm_order(request, current_user)


@router.get(
    "",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("orders.read"))],
    summary="List customer orders",
    description="Retrieves a list of customer orders with optional filtering by warehouse_code, seller_id, or status.",
)
async def list_orders(
    warehouse_code: Optional[str] = Query(None, description="Filter by warehouse code (RENO/COLUMBUS)"),
    seller_id: Optional[str] = Query(None, description="Filter by seller ObjectId string"),
    order_status: Optional[str] = Query(None, alias="status", description="Filter by status (CREATED/CONFIRMED)"),
    current_user: UserModel = Depends(get_current_user),
) -> List[OrderResponse]:
    logger.info(f"GET /v1/orders requested by user {current_user.id}")
    return await order_controller.list_orders(
        warehouse_code=warehouse_code,
        seller_id=seller_id,
        status=order_status,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("orders.read"))],
    summary="Get customer order details",
    description="Retrieves detailed information for a specific customer order by ObjectId string.",
)
async def get_order_by_id(
    order_id: str,
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    logger.info(f"GET /v1/orders/{order_id} requested by user {current_user.id}")
    return await order_controller.get_order_by_id(order_id)
