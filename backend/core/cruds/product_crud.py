from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.product_model import ProductModel

logger = get_logger(__name__)


class ProductCRUD:
    """Database persistence wrapper for Product entity operations.
    Handles MongoDB CRUD queries for product catalog documents.
    """

    @property
    def collection(self):
        """Retrieves the products MongoDB collection instance handle.

        Returns:
            AsyncCollection: The MongoDB products collection object.
        """
        return DatabaseManager.get_db()["products"]

    async def create_product(self, product: ProductModel) -> ProductModel:
        """Inserts a new product document into the database.
        Ensures SKU is stored uppercase and UPC string is sanitized.

        Args:
            product (ProductModel): Product domain data to create.

        Returns:
            ProductModel: The created product instance.
        """
        logger.info(f"Executing ProductCRUD.create_product for SKU {product.sku}")
        product.sku = product.sku.upper().strip()
        if product.upc:
            product.upc = str(product.upc).strip()
        doc = product.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        product.id = str(result.inserted_id)
        return product

    async def get_by_id(self, product_id: str) -> Optional[ProductModel]:
        """Retrieves a product document by string ObjectId.
        Returns None if no matching product is found.

        Args:
            product_id (str): String representation of product ObjectId.

        Returns:
            Optional[ProductModel]: Product model instance if found.
        """
        logger.info(f"Executing ProductCRUD.get_by_id for {product_id}")
        if not ObjectId.is_valid(product_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(product_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return ProductModel(**doc)

    async def get_by_sku(self, sku: str) -> Optional[ProductModel]:
        """Retrieves a product document by unique product SKU string.
        Returns None if no matching product exists.

        Args:
            sku (str): Unique SKU identifier.

        Returns:
            Optional[ProductModel]: Product model instance if found.
        """
        logger.info(f"Executing ProductCRUD.get_by_sku for {sku}")
        normalized_sku = sku.upper().strip()
        doc = await self.collection.find_one({"sku": normalized_sku})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return ProductModel(**doc)

    async def get_by_upc(self, upc: str) -> Optional[ProductModel]:
        """Retrieves a product document by UPC barcode string.
        Preserves string type and leading zeros during search query.

        Args:
            upc (str): UPC barcode string.

        Returns:
            Optional[ProductModel]: Product model instance if found.
        """
        logger.info(f"Executing ProductCRUD.get_by_upc for {upc}")
        normalized_upc = str(upc).strip()
        doc = await self.collection.find_one({"upc": normalized_upc})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return ProductModel(**doc)

    async def update_product(self, product_id: str, update_data: dict) -> Optional[ProductModel]:
        """Updates specific fields of an existing product document.
        Maintains updated_at timestamp and returns updated product model.

        Args:
            product_id (str): String representation of product ObjectId.
            update_data (dict): Dictionary of field updates.

        Returns:
            Optional[ProductModel]: Updated product model instance if found.
        """
        logger.info(f"Executing ProductCRUD.update_product for {product_id}")
        if not ObjectId.is_valid(product_id):
            return None
        if "sku" in update_data:
            update_data["sku"] = update_data["sku"].upper().strip()
        if "upc" in update_data and update_data["upc"] is not None:
            update_data["upc"] = str(update_data["upc"]).strip()
        update_data["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(product_id)},
            {"$set": update_data},
            return_document=True,
        )
        if not result:
            return None
        result["_id"] = str(result["_id"])
        return ProductModel(**result)

    async def list_products(self, seller_id: Optional[str] = None) -> List[ProductModel]:
        """Retrieves registered product documents with optional seller_id filter.
        Returns a list of product models.

        Args:
            seller_id (Optional[str]): Optional filter by seller ObjectId string.

        Returns:
            List[ProductModel]: List of product models.
        """
        logger.info(f"Executing ProductCRUD.list_products (seller_id={seller_id})")
        query = {}
        if seller_id:
            query["seller_id"] = seller_id
        cursor = self.collection.find(query)
        products = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            products.append(ProductModel(**doc))
        return products
