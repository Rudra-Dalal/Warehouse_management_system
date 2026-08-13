import datetime
from typing import List, Optional
from bson import ObjectId
from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.order_model import OrderItemModel, OrderModel

logger = get_logger(__name__)


class OrderCRUD:
    """CRUD operations for the orders MongoDB collection."""

    @property
    def collection(self):
        return DatabaseManager.get_db()["orders"]

    def _to_model(self, doc: dict) -> OrderModel:
        if not doc:
            return None
        doc_copy = dict(doc)
        doc_copy["_id"] = str(doc_copy["_id"])

        raw_items = doc_copy.get("items", [])
        items = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append(OrderItemModel(**item))
            elif isinstance(item, OrderItemModel):
                items.append(item)
        doc_copy["items"] = items

        return OrderModel(**doc_copy)

    async def create_order(
        self,
        order: OrderModel,
        session=None,
    ) -> OrderModel:
        """Persists a new order record to MongoDB.

        Args:
            order (OrderModel): Order model to persist.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            OrderModel: Persisted order with assigned ObjectId string.
        """
        logger.info(f"Executing OrderCRUD.create_order for order_number '{order.order_number}'")
        data = order.model_dump(by_alias=True, exclude={"id"})

        res = await self.collection.insert_one(data, session=session)
        order.id = str(res.inserted_id)
        return order

    async def get_by_id(
        self,
        order_id: str,
        session=None,
    ) -> Optional[OrderModel]:
        """Retrieves an order record by ObjectId string.

        Args:
            order_id (str): Target order ObjectId string.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            Optional[OrderModel]: Matching order or None.
        """
        logger.info(f"Executing OrderCRUD.get_by_id: {order_id}")
        if not ObjectId.is_valid(order_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(order_id)}, session=session)
        return self._to_model(doc) if doc else None

    async def get_by_order_number(
        self,
        order_number: str,
        session=None,
    ) -> Optional[OrderModel]:
        """Retrieves an order record by unique order_number business string.

        Args:
            order_number (str): Target unique order_number string.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            Optional[OrderModel]: Matching order or None.
        """
        logger.info(f"Executing OrderCRUD.get_by_order_number: {order_number}")
        if not order_number:
            return None
        doc = await self.collection.find_one({"order_number": order_number.strip()}, session=session)
        return self._to_model(doc) if doc else None

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        confirmed_at: Optional[datetime.datetime] = None,
        session=None,
    ) -> Optional[OrderModel]:
        """Updates the status and confirmed_at timestamp of an order.

        Args:
            order_id (str): Target order ObjectId string.
            status (str): New status string.
            confirmed_at (Optional[datetime]): Timestamp when order was confirmed.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            Optional[OrderModel]: Updated order model or None.
        """
        logger.info(f"Executing OrderCRUD.update_order_status: {order_id} -> {status}")
        if not ObjectId.is_valid(order_id):
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        update_doc = {
            "status": status,
            "updated_at": now,
        }
        if confirmed_at:
            update_doc["confirmed_at"] = confirmed_at

        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(order_id)},
            {"$set": update_doc},
            return_document=True,
            session=session,
        )
        return self._to_model(doc) if doc else None

    async def list_orders(
        self,
        warehouse_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: Optional[str] = None,
        session=None,
    ) -> List[OrderModel]:
        """Lists orders with optional filtering by warehouse_id, seller_id, or status."""
        logger.info(
            f"Executing OrderCRUD.list_orders filters: wh={warehouse_id}, seller={seller_id}, status={status}"
        )
        query = {}
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if seller_id:
            query["seller_id"] = seller_id
        if status:
            query["status"] = status

        cursor = self.collection.find(query, session=session).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [self._to_model(d) for d in docs]
