from pymongo import ASCENDING
from commons.logger import get_logger
from core.database.database import DatabaseManager

logger = get_logger(__name__)


async def create_database_indexes() -> None:
    """Idempotently creates all required MongoDB database indexes.
    Ensures optimal query performance, unique constraints, and data integrity.
    """
    logger.info("Executing create_database_indexes")
    db = DatabaseManager.get_db()

    # Users collection
    await db["users"].create_index("email", unique=True)

    # Roles collection
    await db["roles"].create_index("name", unique=True)

    # Permissions collection
    await db["permissions"].create_index("name", unique=True)

    # Fixed Warehouses collection
    await db["warehouses"].create_index("code", unique=True)

    # Sellers collection
    await db["sellers"].create_index("code", unique=True)

    # Products collection
    await db["products"].create_index("sku", unique=True)
    try:
        cursor = await db["products"].list_indexes()
        async for idx in cursor:
            if idx.get("name") == "upc_1" and "partialFilterExpression" not in idx:
                await db["products"].drop_index("upc_1")
    except Exception:
        pass

    await db["products"].create_index(
        "upc",
        unique=True,
        partialFilterExpression={"upc": {"$type": "string", "$gt": ""}},
    )

    # Inventory collection: Unique composite index per product per warehouse
    await db["inventory"].create_index(
        [("product_id", ASCENDING), ("warehouse_id", ASCENDING)],
        unique=True,
    )

    # Inventory Movements collection
    await db["inventory_movements"].create_index(
        [("product_id", ASCENDING), ("warehouse_id", ASCENDING)]
    )
    await db["inventory_movements"].create_index("movement_type")
    await db["inventory_movements"].create_index("created_at")

    # Receiving Shipments collection: Unique receiving_reference for duplicate protection & idempotency
    await db["receiving_shipments"].create_index("receiving_reference", unique=True)
    await db["receiving_shipments"].create_index(
        "idempotency_key", unique=True, sparse=True
    )
    await db["receiving_shipments"].create_index("tracking_number")
    await db["receiving_shipments"].create_index("status")

    # Orders collection
    await db["orders"].create_index("order_number", unique=True)
    await db["orders"].create_index("seller_id")
    await db["orders"].create_index("warehouse_id")
    await db["orders"].create_index("status")

    # Audit Logs collection
    await db["audit_logs"].create_index("timestamp")
    await db["audit_logs"].create_index("user_id")
    await db["audit_logs"].create_index("entity_type")
    await db["audit_logs"].create_index("entity_id")
    await db["audit_logs"].create_index("warehouse_id")

    logger.info("Database indexes successfully verified and created")
