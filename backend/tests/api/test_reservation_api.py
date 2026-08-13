import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.product_crud import ProductCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.models.product_model import ProductModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_successful_reservation():
    """Verifies successful stock reservation updates available and reserved quantities and logs a RESERVATION movement."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Reserve Test",
        email="res_admin@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    # Setup Product and Inventory (available=20)
    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="RES_SELLER", name="Res Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="RES-SKU-100", name="Reservation Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 20},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        # Reserve 5 stock units
        res = await client.post(
            f"/v1/inventory/{inv_id}/reserve",
            json={"quantity": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        inv_data = res.json()
        assert inv_data["available_quantity"] == 15
        assert inv_data["reserved_quantity"] == 5

        # Verify RESERVATION movement created
        res_mov = await client.get(
            f"/v1/inventory/{inv_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_mov.status_code == 200
        movements = res_mov.json()
        assert len(movements) == 1
        assert movements[0]["movement_type"] == "RESERVATION"
        assert movements[0]["quantity"] == -5
        assert movements[0]["user_id"] == created_admin.id


@pytest.mark.asyncio
async def test_insufficient_inventory_rejection():
    """Verifies that reserving more than available stock returns HTTP 409 Conflict and creates no movement."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Insufficient Test",
        email="res_insuff@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="RES_INSUFF_SELLER", name="Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="RES-INSUFF-SKU", name="Insuff SKU", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        # Attempt to reserve 6 units against 5 available -> HTTP 409 Conflict
        res = await client.post(
            f"/v1/inventory/{inv_id}/reserve",
            json={"quantity": 6},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 409
        assert "Insufficient inventory" in res.json()["detail"]

        # Verify stock remains available=5, reserved=0
        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_check.json()["available_quantity"] == 5
        assert res_check.json()["reserved_quantity"] == 0

        # Verify NO movement created
        res_mov = await client.get(
            f"/v1/inventory/{inv_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(res_mov.json()) == 0


@pytest.mark.asyncio
async def test_exact_stock_reservation():
    """Verifies reserving exact available stock succeeds (available becomes 0, reserved equals initial available)."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Exact Test",
        email="res_exact@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="RES_EXACT_SELLER", name="Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="RES-EXACT-SKU", name="Exact SKU", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        # Reserve exact stock (5 units)
        res = await client.post(
            f"/v1/inventory/{inv_id}/reserve",
            json={"quantity": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["available_quantity"] == 0
        assert res.json()["reserved_quantity"] == 5


@pytest.mark.asyncio
async def test_invalid_quantity_validation():
    """Verifies reserving 0 or negative quantities returns a validation error."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Invalid Test",
        email="res_invalid@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Reserve 0 units -> 422 Unprocessable Entity
        res_zero = await client.post(
            "/v1/inventory/65c3b1a2f91a2b3c4d5e6f7a/reserve",
            json={"quantity": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_zero.status_code == 422

        # Reserve negative units -> 422 Unprocessable Entity
        res_neg = await client.post(
            "/v1/inventory/65c3b1a2f91a2b3c4d5e6f7a/reserve",
            json={"quantity": -5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_neg.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_inventory_404():
    """Verifies attempting to reserve stock against a non-existent inventory ID returns HTTP 404 Not Found."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin 404 Test",
        email="res_404@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/inventory/65c3b1a2f91a2b3c4d5e6f7a/reserve",
            json={"quantity": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_and_unauthorized_access():
    """Verifies unauthenticated requests return 401 and users lacking permission return 403."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Unauthenticated request -> 401
        res_unauth = await client.post(
            "/v1/inventory/65c3b1a2f91a2b3c4d5e6f7a/reserve",
            json={"quantity": 5},
        )
        assert res_unauth.status_code == 401
