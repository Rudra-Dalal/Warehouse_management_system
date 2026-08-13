from typing import List, Optional
from fastapi import APIRouter, Depends, status

from commons.auth import get_current_user, require_permission
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
from core.controllers.inventory_controller import InventoryController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/inventory", tags=["Inventory"])
inventory_controller = InventoryController()


@router.get("", response_model=List[InventoryResponse])
async def list_inventory(
    warehouse_code: Optional[str] = None,
    sku: Optional[str] = None,
    product_id: Optional[str] = None,
    current_user: UserModel = Depends(require_permission("inventory.read")),
):
    """Lists warehouse stock levels with optional warehouse_code, SKU, or product_id filters.
    Requires 'inventory.read' permission.

    Args:
        warehouse_code (Optional[str]): Warehouse code (RENO or COLUMBUS).
        sku (Optional[str]): Product SKU string.
        product_id (Optional[str]): Product ObjectId.
        current_user (UserModel): Authenticated user.

    Returns:
        List[InventoryResponse]: List of matching inventory records.
    """
    logger.info(f"Calling GET /v1/inventory endpoint by {current_user.email}")
    return await inventory_controller.list_inventory(
        warehouse_code=warehouse_code,
        sku=sku,
        product_id=product_id,
    )


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory(
    request: InventoryCreateRequest,
    current_user: UserModel = Depends(require_permission("inventory.adjust")),
):
    """Registers an initial warehouse inventory record for a Product and Warehouse.
    Requires 'inventory.adjust' permission.

    Args:
        request (InventoryCreateRequest): Inventory creation payload.
        current_user (UserModel): Authenticated user.

    Returns:
        InventoryResponse: The created inventory details.
    """
    logger.info(f"Calling POST /v1/inventory endpoint by {current_user.email}")
    return await inventory_controller.create_inventory(request)


@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory_by_id(
    inventory_id: str,
    current_user: UserModel = Depends(require_permission("inventory.read")),
):
    """Retrieves specific inventory details by string ObjectId.
    Requires 'inventory.read' permission.

    Args:
        inventory_id (str): Target inventory ObjectId string.
        current_user (UserModel): Authenticated user.

    Returns:
        InventoryResponse: Target inventory details.
    """
    logger.info(f"Calling GET /v1/inventory/{inventory_id} endpoint by {current_user.email}")
    return await inventory_controller.get_inventory_by_id(inventory_id)


@router.patch("/{inventory_id}/adjust", response_model=InventoryResponse)
async def adjust_inventory(
    inventory_id: str,
    request: InventoryAdjustmentRequest,
    current_user: UserModel = Depends(require_permission("inventory.adjust")),
):
    """Adjusts available stock levels using a signed quantity delta and logs an InventoryMovement.
    Requires 'inventory.adjust' permission.

    Args:
        inventory_id (str): Target inventory ObjectId string.
        request (InventoryAdjustmentRequest): Signed quantity adjustment parameters.
        current_user (UserModel): Authenticated user performing adjustment.

    Returns:
        InventoryResponse: Updated inventory state response.
    """
    logger.info(f"Calling PATCH /v1/inventory/{inventory_id}/adjust endpoint by {current_user.email}")
    return await inventory_controller.adjust_inventory(
        inventory_id=inventory_id,
        request=request,
        current_user=current_user,
    )


@router.post("/{inventory_id}/reserve", response_model=InventoryResponse)
async def reserve_inventory(
    inventory_id: str,
    request: InventoryReservationRequest,
    current_user: UserModel = Depends(require_permission("inventory.reserve")),
):
    """Atomically reserves stock for orders using an atomic MongoDB conditional update.
    Requires 'inventory.reserve' permission.

    Args:
        inventory_id (str): Target inventory ObjectId string.
        request (InventoryReservationRequest): Positive integer reservation quantity.
        current_user (UserModel): Authenticated user requesting reservation.

    Returns:
        InventoryResponse: Updated inventory state response.
    """
    logger.info(f"Calling POST /v1/inventory/{inventory_id}/reserve endpoint by {current_user.email}")
    return await inventory_controller.reserve_inventory(
        inventory_id=inventory_id,
        request=request,
        current_user=current_user,
    )


@router.get("/{inventory_id}/movements", response_model=List[InventoryMovementResponse])
async def list_inventory_movements(
    inventory_id: str,
    current_user: UserModel = Depends(require_permission("inventory.read")),
):
    """Retrieves historical InventoryMovement change logs for an inventory context.
    Requires 'inventory.read' permission.

    Args:
        inventory_id (str): Target inventory ObjectId string.
        current_user (UserModel): Authenticated user.

    Returns:
        List[InventoryMovementResponse]: Historical movement log entries.
    """
    logger.info(f"Calling GET /v1/inventory/{inventory_id}/movements endpoint by {current_user.email}")
    return await inventory_controller.list_movements(inventory_id)
