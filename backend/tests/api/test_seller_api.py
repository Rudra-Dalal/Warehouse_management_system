import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_seller_lifecycle_and_uniqueness():
    """Verifies Seller CRUD API endpoints, code uniqueness validation, and retrieval."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Seller Test",
        email="sellertest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create Seller 1
        res1 = await client.post(
            "/v1/sellers",
            json={"code": "ACME", "name": "ACME Corporation", "email": "acme@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 201
        s1 = res1.json()
        assert s1["code"] == "ACME"
        seller_id = s1["id"]

        # Duplicate Code Creation -> 409
        res_dup = await client.post(
            "/v1/sellers",
            json={"code": "acme", "name": "ACME Duplicate"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dup.status_code == 409

        # Retrieve Seller
        res_get = await client.get(
            f"/v1/sellers/{seller_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_get.status_code == 200
        assert res_get.json()["name"] == "ACME Corporation"

        # List Sellers
        res_list = await client.get(
            "/v1/sellers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1


@pytest.mark.asyncio
async def test_seller_authorization_restrictions():
    """Verifies WAREHOUSE_STAFF lacking 'sellers.manage' receives HTTP 403 on POST /v1/sellers."""
    role_crud = RoleCRUD()
    staff_role = await role_crud.get_by_name("WAREHOUSE_STAFF")

    user_crud = UserCRUD()
    staff_user = UserModel(
        name="Staff Seller Test",
        email="staffseller@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=staff_role.id,
        is_active=True,
    )
    created_staff = await user_crud.create_user(staff_user)
    token = create_access_token(subject=created_staff.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/sellers",
            json={"code": "FORBIDDEN", "name": "Forbidden Seller"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
