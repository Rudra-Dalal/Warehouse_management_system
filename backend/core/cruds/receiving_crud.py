import datetime
from typing import List, Optional
from bson import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.collection import AsyncCollection

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.models.receiving_model import ReceivingItemModel, ReceivingShipmentModel

logger = get_logger(__name__)


class ReceivingCRUD:
    """CRUD operations for inbound warehouse receiving shipments in MongoDB."""

    @property
    def collection(self) -> AsyncCollection:
        return DatabaseManager.get_db()["receiving_shipments"]

    async def create_receiving_shipment(
        self,
        shipment: ReceivingShipmentModel,
        session: Optional[AsyncClientSession] = None,
    ) -> ReceivingShipmentModel:
        """Inserts a new receiving shipment record into MongoDB.

        Args:
            shipment (ReceivingShipmentModel): The receiving shipment to create.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            ReceivingShipmentModel: Created receiving shipment with assigned ObjectId.
        """
        logger.info(f"Executing ReceivingCRUD.create_receiving_shipment: {shipment.receiving_reference}")
        doc = shipment.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc, session=session)
        shipment.id = str(result.inserted_id)
        return shipment

    async def get_by_id(
        self,
        shipment_id: str,
        session: Optional[AsyncClientSession] = None,
    ) -> Optional[ReceivingShipmentModel]:
        """Retrieves a receiving shipment document by its MongoDB ObjectId string.

        Args:
            shipment_id (str): Target receiving shipment ObjectId string.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[ReceivingShipmentModel]: Shipment model if found, None otherwise.
        """
        logger.info(f"Executing ReceivingCRUD.get_by_id: {shipment_id}")
        if not ObjectId.is_valid(shipment_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(shipment_id)}, session=session)
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return ReceivingShipmentModel(**doc)

    async def get_by_reference(
        self,
        receiving_reference: str,
        session: Optional[AsyncClientSession] = None,
    ) -> Optional[ReceivingShipmentModel]:
        """Retrieves a receiving shipment document by its unique receiving_reference.

        Args:
            receiving_reference (str): Unique reference code (e.g. WH-REC-001).
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[ReceivingShipmentModel]: Shipment model if found, None otherwise.
        """
        logger.info(f"Executing ReceivingCRUD.get_by_reference: {receiving_reference}")
        doc = await self.collection.find_one({"receiving_reference": receiving_reference}, session=session)
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return ReceivingShipmentModel(**doc)

    async def update_shipment_status(
        self,
        shipment_id: str,
        status: str,
        received_at: Optional[datetime.datetime] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> Optional[ReceivingShipmentModel]:
        """Updates the status and optional received_at timestamp of a receiving shipment.

        Args:
            shipment_id (str): Target shipment ObjectId string.
            status (str): New status string (e.g. RECEIVED, FAILED).
            received_at (Optional[datetime]): Timestamp of completion.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            Optional[ReceivingShipmentModel]: Updated shipment model if found, None otherwise.
        """
        logger.info(f"Executing ReceivingCRUD.update_shipment_status: {shipment_id} -> {status}")
        if not ObjectId.is_valid(shipment_id):
            return None
        now = datetime.datetime.now(datetime.timezone.utc)
        update_doc = {
            "status": status,
            "updated_at": now,
        }
        if received_at is not None:
            update_doc["received_at"] = received_at

        await self.collection.update_one(
            {"_id": ObjectId(shipment_id)},
            {"$set": update_doc},
            session=session,
        )
        return await self.get_by_id(shipment_id, session=session)

    async def list_receiving_shipments(
        self,
        warehouse_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> List[ReceivingShipmentModel]:
        """Lists receiving shipments filtered by warehouse or seller.

        Args:
            warehouse_id (Optional[str]): Optional warehouse ObjectId filter.
            seller_id (Optional[str]): Optional seller ObjectId filter.
            session (Optional[AsyncClientSession]): Active MongoDB transaction session.

        Returns:
            List[ReceivingShipmentModel]: List of matching receiving shipments.
        """
        logger.info("Executing ReceivingCRUD.list_receiving_shipments")
        query = {}
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if seller_id:
            query["seller_id"] = seller_id

        cursor = self.collection.find(query, session=session).sort("created_at", -1)
        shipments = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            shipments.append(ReceivingShipmentModel(**doc))
        return shipments
