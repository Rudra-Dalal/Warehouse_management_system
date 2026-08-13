from typing import List, Optional
from fastapi import HTTPException, status

from commons.logger import get_logger
from core.apis.schemas.requests.product_request import ProductCreateRequest, ProductUpdateRequest
from core.apis.schemas.responses.product_response import ProductResponse
from core.cruds.product_crud import ProductCRUD
from core.cruds.seller_crud import SellerCRUD
from core.models.product_model import ProductModel

logger = get_logger(__name__)


class ProductController:
    """Business logic controller handling product creation, SKU lookup, and UPC barcode resolution.
    Validates seller existence, SKU uniqueness, and UPC string uniqueness constraints.
    """

    def __init__(self):
        """Initializes ProductController with ProductCRUD and SellerCRUD instances."""
        self.product_crud = ProductCRUD()
        self.seller_crud = SellerCRUD()

    async def list_products(self, seller_id: Optional[str] = None) -> List[ProductResponse]:
        """Retrieves registered products with optional seller_id filter.
        Returns a list of public ProductResponse schemas.

        Args:
            seller_id (Optional[str]): Optional seller ObjectId filter.

        Returns:
            List[ProductResponse]: List of matching product catalog items.
        """
        logger.info(f"Executing ProductController.list_products (seller_id={seller_id})")
        products = await self.product_crud.list_products(seller_id=seller_id)
        return [
            ProductResponse(
                id=p.id,
                sku=p.sku,
                name=p.name,
                description=p.description,
                upc=p.upc,
                seller_id=p.seller_id,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in products
        ]

    async def get_product_by_id(self, product_id: str) -> ProductResponse:
        """Retrieves a specific product catalog item by string ObjectId.
        Raises HTTP 404 Not Found if no product exists.

        Args:
            product_id (str): Target product ObjectId string.

        Returns:
            ProductResponse: Target product details.
        """
        logger.info(f"Executing ProductController.get_product_by_id for {product_id}")
        product = await self.product_crud.get_by_id(product_id)
        if not product:
            logger.warning(f"Product ID {product_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return ProductResponse(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            upc=product.upc,
            seller_id=product.seller_id,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def get_product_by_sku(self, sku: str) -> ProductResponse:
        """Retrieves a product catalog item by unique SKU business identifier.
        Raises HTTP 404 Not Found if no product matches the SKU.

        Args:
            sku (str): SKU string identifier.

        Returns:
            ProductResponse: Matching product details.
        """
        logger.info(f"Executing ProductController.get_product_by_sku for {sku}")
        product = await self.product_crud.get_by_sku(sku)
        if not product:
            logger.warning(f"Product SKU {sku} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with SKU '{sku}' not found",
            )
        return ProductResponse(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            upc=product.upc,
            seller_id=product.seller_id,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def get_product_by_upc(self, upc: str) -> ProductResponse:
        """Resolves a product catalog item by UPC barcode string.
        Preserves string matching to accurately retain leading zeros.

        Args:
            upc (str): Scanned UPC barcode string.

        Returns:
            ProductResponse: Matching product details.
        """
        logger.info(f"Executing ProductController.get_product_by_upc for {upc}")
        product = await self.product_crud.get_by_upc(upc)
        if not product:
            logger.warning(f"Product UPC {upc} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with UPC '{upc}' not found",
            )
        return ProductResponse(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            upc=product.upc,
            seller_id=product.seller_id,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def create_product(self, request: ProductCreateRequest) -> ProductResponse:
        """Registers a new product catalog item with SKU and UPC uniqueness checks.
        Validates seller_id existence; raises 404 for missing seller or 409 for conflicts.

        Args:
            request (ProductCreateRequest): Product creation payload.

        Returns:
            ProductResponse: The created product details.
        """
        logger.info(f"Executing ProductController.create_product for SKU {request.sku}")
        seller = await self.seller_crud.get_by_id(request.seller_id)
        if not seller:
            logger.warning(f"Product creation failed: Seller ID {request.seller_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with ID '{request.seller_id}' not found",
            )

        existing_sku = await self.product_crud.get_by_sku(request.sku)
        if existing_sku:
            logger.warning(f"Product creation failed: SKU {request.sku} already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{request.sku}' already exists",
            )

        if request.upc:
            normalized_upc = str(request.upc).strip()
            if normalized_upc:
                existing_upc = await self.product_crud.get_by_upc(normalized_upc)
                if existing_upc:
                    logger.warning(f"Product creation failed: UPC {normalized_upc} already registered")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Product with UPC '{normalized_upc}' already exists",
                    )

        new_product = ProductModel(
            sku=request.sku,
            name=request.name,
            description=request.description,
            upc=str(request.upc).strip() if request.upc else None,
            seller_id=request.seller_id,
            is_active=True,
        )
        created = await self.product_crud.create_product(new_product)
        return ProductResponse(
            id=created.id,
            sku=created.sku,
            name=created.name,
            description=created.description,
            upc=created.upc,
            seller_id=created.seller_id,
            is_active=created.is_active,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def update_product(
        self, product_id: str, request: ProductUpdateRequest
    ) -> ProductResponse:
        """Updates specific fields of a product catalog item.
        Validates UPC uniqueness if UPC string is updated.

        Args:
            product_id (str): Target product ObjectId string.
            request (ProductUpdateRequest): Field update data.

        Returns:
            ProductResponse: The updated product details.
        """
        logger.info(f"Executing ProductController.update_product for {product_id}")
        existing = await self.product_crud.get_by_id(product_id)
        if not existing:
            logger.warning(f"Product update failed: Product ID {product_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )

        update_fields = {}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.description is not None:
            update_fields["description"] = request.description
        if request.is_active is not None:
            update_fields["is_active"] = request.is_active
        if request.upc is not None:
            normalized_upc = str(request.upc).strip() if request.upc else None
            if normalized_upc:
                existing_upc = await self.product_crud.get_by_upc(normalized_upc)
                if existing_upc and existing_upc.id != product_id:
                    logger.warning(f"Product update failed: UPC {normalized_upc} belongs to another product")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Product with UPC '{normalized_upc}' already exists",
                    )
            update_fields["upc"] = normalized_upc

        if not update_fields:
            return ProductResponse(
                id=existing.id,
                sku=existing.sku,
                name=existing.name,
                description=existing.description,
                upc=existing.upc,
                seller_id=existing.seller_id,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

        updated = await self.product_crud.update_product(product_id, update_fields)
        return ProductResponse(
            id=updated.id,
            sku=updated.sku,
            name=updated.name,
            description=updated.description,
            upc=updated.upc,
            seller_id=updated.seller_id,
            is_active=updated.is_active,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
