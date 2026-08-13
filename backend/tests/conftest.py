import pytest_asyncio
from core.config import settings
from core.database.database import DatabaseManager, seed_fixed_warehouses
from core.database.seed_rbac import seed_rbac_data
from core.database.indexes import create_database_indexes


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Pytest fixture isolating test data in whitfield_wms_test database.
    Initializes test database, seeds warehouses and RBAC data, and cleans up after tests.
    """
    settings.DATABASE_NAME = "whitfield_wms_test"
    await DatabaseManager.connect_to_database()
    db = DatabaseManager.get_db()

    # Clean existing test collections
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].delete_many({})

    await seed_fixed_warehouses()
    await seed_rbac_data()
    await create_database_indexes()

    yield db

    # Cleanup test collections after test execution
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].delete_many({})
    await DatabaseManager.close_database_connection()
