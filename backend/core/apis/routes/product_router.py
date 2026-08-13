from typing import List, Optional
from fastapi import APIRouter, Depends, status

from commons.auth import get_current_user, require_permission
from commons.logger import get_logger
from core.apis.schemas.requests.product_request import ProductCreateRequest, ProductUpdateRequest
from core.apis.schemas.responses.product_response import ProductResponse
from core.controllers.product_controller import ProductController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/products", tags=["Products"])
product_controller = ProductController()


@router.get("", response_model=List[ProductResponse])
async def list_products(
    seller_id: Optional[str] = None,
    current_user: UserModel = Depends(require_permission("products.read")),
):
    """Lists registered products with optional seller_id query filter.
    Requires 'products.read' permission.

    Args:
        seller_id (Optional[str]): Optional seller ObjectId filter.
        current_user (UserModel): Authenticated user.

    Returns:
        List[ProductResponse]: List of matching product catalog items.
    """
    logger.info(f"Calling GET /v1/products endpoint by {current_user.email}")
    return await product_controller.list_products(seller_id=seller_id)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreateRequest,
    current_user: UserModel = Depends(require_permission("products.manage")),
):
    """Registers a new product catalog item.
    Requires 'products.manage' permission.

    Args:
        request (ProductCreateRequest): Product creation payload.
        current_user (UserModel): Authenticated user.

    Returns:
        ProductResponse: The created product details.
    """
    logger.info(f"Calling POST /v1/products endpoint by {current_user.email}")
    return await product_controller.create_product(request, current_user)


@router.get("/by-sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(
    sku: str,
    current_user: UserModel = Depends(require_permission("products.read")),
):
    """Looks up a product by unique SKU business identifier.
    Requires 'products.read' permission.

    Args:
        sku (str): Target SKU string.
        current_user (UserModel): Authenticated user.

    Returns:
        ProductResponse: Matching product details.
    """
    logger.info(f"Calling GET /v1/products/by-sku/{sku} endpoint by {current_user.email}")
    return await product_controller.get_product_by_sku(sku)


@router.get("/by-upc/{upc}", response_model=ProductResponse)
async def get_product_by_upc(
    upc: str,
    current_user: UserModel = Depends(require_permission("products.read")),
):
    """Resolves a product by UPC barcode string (preserving leading zeros).
    Requires 'products.read' permission.

    Args:
        upc (str): Target UPC barcode string.
        current_user (UserModel): Authenticated user.

    Returns:
        ProductResponse: Matching product details.
    """
    logger.info(f"Calling GET /v1/products/by-upc/{upc} endpoint by {current_user.email}")
    return await product_controller.get_product_by_upc(upc)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id(
    product_id: str,
    current_user: UserModel = Depends(require_permission("products.read")),
):
    """Retrieves product catalog details by string ObjectId.
    Requires 'products.read' permission.

    Args:
        product_id (str): Target product ObjectId string.
        current_user (UserModel): Authenticated user.

    Returns:
        ProductResponse: Target product details response.
    """
    logger.info(f"Calling GET /v1/products/{product_id} endpoint by {current_user.email}")
    return await product_controller.get_product_by_id(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    current_user: UserModel = Depends(require_permission("products.manage")),
):
    """Updates product catalog item details or UPC string.
    Requires 'products.manage' permission.

    Args:
        product_id (str): Target product ObjectId string.
        request (ProductUpdateRequest): Field update data.
        current_user (UserModel): Authenticated user.

    Returns:
        ProductResponse: Updated product details response.
    """
    logger.info(f"Calling PATCH /v1/products/{product_id} endpoint by {current_user.email}")
    return await product_controller.update_product(product_id, request)
