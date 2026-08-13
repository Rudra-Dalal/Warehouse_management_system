import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from core.database.database import DatabaseManager, seed_fixed_warehouses


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verifies the GET /health endpoint returns a 200 status code and healthy JSON payload.
    Ensures that the FastAPI app and database ping succeed.
    """
    await DatabaseManager.connect_to_database()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_fixed_warehouse_seeding_and_idempotency():
    """Verifies that RENO and COLUMBUS warehouses are idempotently seeded in MongoDB.
    Ensures re-running seed_fixed_warehouses does not create duplicate entries.
    """
    await DatabaseManager.connect_to_database()
    db = DatabaseManager.get_db()

    # Re-run seeding to verify idempotency
    await seed_fixed_warehouses()
    await seed_fixed_warehouses()

    warehouses = await db["warehouses"].find({}).to_list()
    codes = [w["code"] for w in warehouses]

    assert "RENO" in codes
    assert "COLUMBUS" in codes
    assert len(warehouses) == 2
