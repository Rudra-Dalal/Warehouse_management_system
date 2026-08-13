import datetime
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from commons.logger import get_logger
from core.config import settings

logger = get_logger(__name__)

class DatabaseManager:
    """Manages asynchronous MongoDB connection lifecycle and collection handles.
    Provides methods for connecting, disconnecting, and retrieving active database instances.
    """

    client: Optional[AsyncMongoClient] = None
    db: Optional[AsyncDatabase] = None

    @classmethod
    async def connect_to_database(cls) -> None:
        """Establishes connection to MongoDB using PyMongo AsyncMongoClient.
        Initializes the database reference and logs connection status.
        """
        logger.info("Executing DatabaseManager.connect_to_database")
        try:
            cls.client = AsyncMongoClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DATABASE_NAME]
            # Ping database to verify connection
            await cls.db.command("ping")
            logger.info(f"Successfully connected to MongoDB at {settings.MONGODB_URL}")
        except Exception as error:
            logger.error(f"Error in DatabaseManager.connect_to_database: {error}")
            raise error

    @classmethod
    async def close_database_connection(cls) -> None:
        """Closes the active MongoDB client connection session.
        Ensures resources are cleaned up during application shutdown.
        """
        logger.info("Executing DatabaseManager.close_database_connection")
        if cls.client:
            await cls.client.close()
            logger.info("Closed MongoDB client connection")

    @classmethod
    def get_db(cls) -> AsyncDatabase:
        """Retrieves the current active AsyncDatabase reference instance.
        Raises an exception if the database client has not been initialized.

        Returns:
            AsyncDatabase: The active database connection instance.
        """
        if cls.db is None:
            raise RuntimeError("Database connection has not been initialized.")
        return cls.db


async def seed_fixed_warehouses() -> None:
    """Idempotently seeds the fixed Reno and Columbus warehouse entities.
    Ensures that running initialization multiple times never creates duplicates.
    """
    logger.info("Executing seed_fixed_warehouses")
    db = DatabaseManager.get_db()
    warehouses_collection = db["warehouses"]

    # Ensure unique index on code
    await warehouses_collection.create_index("code", unique=True)

    fixed_warehouses = [
        {
            "code": "RENO",
            "name": "Reno Warehouse",
            "city": "Reno",
            "state": "NV",
            "is_active": True,
        },
        {
            "code": "COLUMBUS",
            "name": "Columbus Warehouse",
            "city": "Columbus",
            "state": "OH",
            "is_active": True,
        },
    ]

    for warehouse_data in fixed_warehouses:
        existing = await warehouses_collection.find_one({"code": warehouse_data["code"]})
        if not existing:
            warehouse_data["created_at"] = datetime.datetime.now(datetime.timezone.utc)
            warehouse_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
            await warehouses_collection.insert_one(warehouse_data)
            logger.info(f"Seeded fixed warehouse: {warehouse_data['code']}")
        else:
            logger.info(f"Fixed warehouse {warehouse_data['code']} already exists")

# Module-level singleton for compatibility with existing imports
# It reuses the same DatabaseManager class, which is initialized during the FastAPI startup lifecycle.
# The instance does not create a new MongoClient; it will hold the same client once DatabaseManager.connect_to_database() is called.

db_manager = DatabaseManager()

__all__ = ["DatabaseManager", "db_manager"]
