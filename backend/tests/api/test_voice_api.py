import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from commons.security import create_access_token, hash_password
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel

pytestmark = pytest.mark.asyncio


async def get_test_headers(email: str = "voiceuser@example.com"):
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")
    user_crud = UserCRUD()

    existing = await user_crud.get_by_email(email)
    if not existing:
        user = UserModel(
            name="Voice User",
            email=email,
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
        existing = await user_crud.create_user(user)

    token = create_access_token(subject=existing.id)
    return {"Authorization": f"Bearer {token}"}


async def test_voice_command_inventory_lookup():
    headers = await get_test_headers("voice_inv@example.com")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = {
            "transcript": "Show inventory for SKU 1048",
            "intent": "inventory_lookup",
            "entities": {"sku": "SKU-1048"},
            "confirmed": False,
        }
        res = await ac.post("/v1/voice/command", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "inventory_lookup"
        assert data["status"] == "success"


async def test_voice_command_mutating_requires_confirmation():
    headers = await get_test_headers("voice_mut@example.com")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = {
            "transcript": "Adjust inventory for SKU 1048 by 10",
            "intent": "adjust_inventory",
            "entities": {"sku": "SKU-1048", "quantity": 10},
            "confirmed": False,
        }
        res = await ac.post("/v1/voice/command", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "confirmation_required"
        assert data["requires_confirmation"] is True
