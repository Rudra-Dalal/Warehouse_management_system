from typing import List
from fastapi import APIRouter, Depends, status

from commons.auth import get_current_user, require_permission
from commons.logger import get_logger
from core.apis.schemas.requests.seller_request import SellerCreateRequest, SellerUpdateRequest
from core.apis.schemas.responses.seller_response import SellerResponse
from core.controllers.seller_controller import SellerController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/sellers", tags=["Sellers"])
seller_controller = SellerController()


@router.get("", response_model=List[SellerResponse])
async def list_sellers(
    current_user: UserModel = Depends(require_permission("sellers.read")),
):
    """Lists all e-commerce seller clients.
    Requires 'sellers.read' permission.

    Args:
        current_user (UserModel): Authenticated user.

    Returns:
        List[SellerResponse]: List of all registered sellers.
    """
    logger.info(f"Calling GET /v1/sellers endpoint by {current_user.email}")
    return await seller_controller.list_sellers()


@router.post("", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    request: SellerCreateRequest,
    current_user: UserModel = Depends(require_permission("sellers.manage")),
):
    """Registers a new e-commerce seller client.
    Requires 'sellers.manage' permission.

    Args:
        request (SellerCreateRequest): Seller registration data.
        current_user (UserModel): Authenticated user.

    Returns:
        SellerResponse: The created seller details.
    """
    logger.info(f"Calling POST /v1/sellers endpoint by {current_user.email}")
    return await seller_controller.create_seller(request, current_user)


@router.get("/{seller_id}", response_model=SellerResponse)
async def get_seller_by_id(
    seller_id: str,
    current_user: UserModel = Depends(require_permission("sellers.read")),
):
    """Retrieves seller profile details by ObjectId string.
    Requires 'sellers.read' permission.

    Args:
        seller_id (str): Target seller ObjectId string.
        current_user (UserModel): Authenticated user.

    Returns:
        SellerResponse: Target seller profile.
    """
    logger.info(f"Calling GET /v1/sellers/{seller_id} endpoint by {current_user.email}")
    return await seller_controller.get_seller_by_id(seller_id)


@router.patch("/{seller_id}", response_model=SellerResponse)
async def update_seller(
    seller_id: str,
    request: SellerUpdateRequest,
    current_user: UserModel = Depends(require_permission("sellers.manage")),
):
    """Updates seller profile details or active status.
    Requires 'sellers.manage' permission.

    Args:
        seller_id (str): Target seller ObjectId string.
        request (SellerUpdateRequest): Field update data.
        current_user (UserModel): Authenticated user.

    Returns:
        SellerResponse: Updated seller details response.
    """
    logger.info(f"Calling PATCH /v1/sellers/{seller_id} endpoint by {current_user.email}")
    return await seller_controller.update_seller(seller_id, request, current_user)
