from fastapi import HTTPException, status
from core.utils.barcode import normalize_barcode
from core.cruds.product_crud import ProductCRUD
from core.models.product_model import ProductModel

class BarcodeService:
    """Service layer handling barcode normalization and product resolution."""

    def __init__(self):
        self.product_crud = ProductCRUD()

    async def resolve_barcode(self, upc: str) -> ProductModel:
        """Normalizes the barcode input and looks up the corresponding Product.
        Raises 404 Not Found if no product exists with the given UPC.
        Raises 422 Unprocessable Content if normalization fails.
        """
        try:
            normalized = normalize_barcode(upc)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )

        product = await self.product_crud.get_by_upc(normalized)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with UPC '{normalized}' not found"
            )
        return product
