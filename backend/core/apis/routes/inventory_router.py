from typing import List, Optional
from fastapi import APIRouter, Depends, status

from commons.auth import get_current_user, require_permission, authorize_warehouse
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
    if warehouse_code:
        await authorize_warehouse(current_user, warehouse_code)
    else:
        # If no specific warehouse is requested, we can let it pass,
        # but in a real system we might want to filter the results 
        # to only those the user is assigned to. For now, since they 
        # didn't specify one, authorize_warehouse handles it via returning True.
        # But wait, if they don't specify, they could see inventory for unauthorized warehouses!
        # The prompt says "GET inventory?warehouse=COLUMBUS -> 403 FORBIDDEN. Similarly protect: - inventory".
        # Let's enforce that if they are NOT admin, they MUST provide a warehouse_code OR we filter.
        # It's better to fetch and filter in controller, or just require it here if not admin.
        pass

    results = await inventory_controller.list_inventory(
        warehouse_code=warehouse_code,
        sku=sku,
        product_id=product_id,
    )
    
    # Filter results for non-admins if no warehouse_code was provided
    if not warehouse_code:
        # Check if they are admin
        from core.cruds.role_crud import RoleCRUD
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != "ADMIN":
            results = [r for r in results if r.warehouse_code in current_user.assigned_warehouse_ids]

    return results


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
    await authorize_warehouse(current_user, request.warehouse_code)
    return await inventory_controller.create_inventory(request, current_user=current_user)


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
    result = await inventory_controller.get_inventory_by_id(inventory_id)
    await authorize_warehouse(current_user, result.warehouse_code)
    return result


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
    # We must fetch the inventory first to know its warehouse
    inv = await inventory_controller.get_inventory_by_id(inventory_id)
    await authorize_warehouse(current_user, inv.warehouse_code)

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
    inv = await inventory_controller.get_inventory_by_id(inventory_id)
    await authorize_warehouse(current_user, inv.warehouse_code)
    
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
    inv = await inventory_controller.get_inventory_by_id(inventory_id)
    await authorize_warehouse(current_user, inv.warehouse_code)

    return await inventory_controller.list_movements(inventory_id)
