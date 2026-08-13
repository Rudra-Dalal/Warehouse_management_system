import datetime
from typing import List, Optional
from bson import ObjectId
from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.fulfillment_model import (
    FulfillmentItemModel,
    FulfillmentModel,
    FulfillmentStatus,
)

logger = get_logger(__name__)


class FulfillmentCRUD:
    """CRUD persistence operations for the fulfillments MongoDB collection."""

    @property
    def collection(self):
        return DatabaseManager.get_db()["fulfillments"]

    def _to_model(self, doc: dict) -> Optional[FulfillmentModel]:
        if not doc:
            return None
        doc_copy = dict(doc)
        doc_copy["_id"] = str(doc_copy["_id"])

        raw_items = doc_copy.get("items", [])
        items = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append(FulfillmentItemModel(**item))
            elif isinstance(item, FulfillmentItemModel):
                items.append(item)
        doc_copy["items"] = items

        return FulfillmentModel(**doc_copy)

    async def create_fulfillment(
        self,
        fulfillment: FulfillmentModel,
        session=None,
    ) -> FulfillmentModel:
        """Persists a new fulfillment record to MongoDB.

        Args:
            fulfillment (FulfillmentModel): Fulfillment model to persist.
            session (Optional[AsyncClientSession]): Active MongoDB session.

        Returns:
            FulfillmentModel: Persisted model with assigned ObjectId string.
        """
        logger.info(f"Executing FulfillmentCRUD.create_fulfillment for order_id '{fulfillment.order_id}'")
        data = fulfillment.model_dump(by_alias=True, exclude_none=True)

        if "_id" in data:
            if isinstance(data["_id"], str) and ObjectId.is_valid(data["_id"]):
                data["_id"] = ObjectId(data["_id"])
            elif not isinstance(data["_id"], ObjectId):
                data.pop("_id")

        res = await self.collection.insert_one(data, session=session)
        if not fulfillment.id:
            fulfillment.id = str(res.inserted_id)
        return fulfillment

    async def get_by_id(
        self,
        fulfillment_id: str,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Retrieves a fulfillment record by ObjectId string."""
        logger.info(f"Executing FulfillmentCRUD.get_by_id: {fulfillment_id}")
        if not ObjectId.is_valid(fulfillment_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(fulfillment_id)}, session=session)
        return self._to_model(doc) if doc else None

    async def get_by_order_id(
        self,
        order_id: str,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Retrieves a fulfillment record by associated order_id string."""
        logger.info(f"Executing FulfillmentCRUD.get_by_order_id: {order_id}")
        if not order_id:
            return None
        doc = await self.collection.find_one({"order_id": order_id.strip()}, session=session)
        return self._to_model(doc) if doc else None

    async def list_fulfillments(
        self,
        warehouse_id: Optional[str] = None,
        status: Optional[str] = None,
        session=None,
    ) -> List[FulfillmentModel]:
        """Lists fulfillment records with optional warehouse_id and status filtering."""
        logger.info(f"Executing FulfillmentCRUD.list_fulfillments filters: wh={warehouse_id}, status={status}")
        query = {}
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if status:
            query["status"] = status

        cursor = self.collection.find(query, session=session).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [self._to_model(d) for d in docs]

    async def update_status(
        self,
        fulfillment_id: str,
        status: str,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Updates the status of a fulfillment record."""
        logger.info(f"Executing FulfillmentCRUD.update_status: {fulfillment_id} -> {status}")
        if not ObjectId.is_valid(fulfillment_id):
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(fulfillment_id)},
            {"$set": {"status": status, "updated_at": now}},
            return_document=True,
            session=session,
        )
        return self._to_model(doc) if doc else None

    async def update_pick_progress(
        self,
        fulfillment_id: str,
        items: List[FulfillmentItemModel],
        picked_by_user_id: str,
        picked_at: datetime.datetime,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Updates pick progress, items, and picked metadata on a fulfillment record.

        Transitions status to PICKED.
        """
        logger.info(f"Executing FulfillmentCRUD.update_pick_progress for {fulfillment_id} by user {picked_by_user_id}")
        if not ObjectId.is_valid(fulfillment_id):
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        item_dicts = [it.model_dump() for it in items]
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(fulfillment_id)},
            {
                "$set": {
                    "status": FulfillmentStatus.PICKED.value,
                    "items": item_dicts,
                    "picked_by_user_id": picked_by_user_id,
                    "picked_at": picked_at,
                    "updated_at": now,
                }
            },
            return_document=True,
            session=session,
        )
        return self._to_model(doc) if doc else None

    async def update_pack_progress(
        self,
        fulfillment_id: str,
        items: List[FulfillmentItemModel],
        packed_by_user_id: str,
        packed_at: datetime.datetime,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Updates pack progress, items, and packed metadata on a fulfillment record.

        Transitions status to PACKED.
        """
        logger.info(f"Executing FulfillmentCRUD.update_pack_progress for {fulfillment_id} by user {packed_by_user_id}")
        if not ObjectId.is_valid(fulfillment_id):
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        item_dicts = [it.model_dump() for it in items]
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(fulfillment_id)},
            {
                "$set": {
                    "status": FulfillmentStatus.PACKED.value,
                    "items": item_dicts,
                    "packed_by_user_id": packed_by_user_id,
                    "packed_at": packed_at,
                    "updated_at": now,
                }
            },
            return_document=True,
            session=session,
        )
        return self._to_model(doc) if doc else None

    async def update_shipping_state(
        self,
        fulfillment_id: str,
        shipped_by_user_id: str,
        shipped_at: datetime.datetime,
        session=None,
    ) -> Optional[FulfillmentModel]:
        """Updates shipping metadata and transitions status to SHIPPED."""
        logger.info(f"Executing FulfillmentCRUD.update_shipping_state for {fulfillment_id} by user {shipped_by_user_id}")
        if not ObjectId.is_valid(fulfillment_id):
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(fulfillment_id)},
            {
                "$set": {
                    "status": FulfillmentStatus.SHIPPED.value,
                    "shipped_by_user_id": shipped_by_user_id,
                    "shipped_at": shipped_at,
                    "updated_at": now,
                }
            },
            return_document=True,
            session=session,
        )
        return self._to_model(doc) if doc else None
