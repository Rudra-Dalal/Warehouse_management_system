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
async def test_inventory_creation_and_warehouse_isolation():
    """Verifies warehouse-specific inventory creation, composite product+warehouse uniqueness, and warehouse isolation."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Inventory Test",
        email="invtest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    # Setup Seller and Product
    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="INV_SELLER", name="Inv Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="INV-SKU-100", name="Inventory Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create Inventory for Product + RENO
        res_reno = await client.post(
            "/v1/inventory",
            json={
                "product_id": product.id,
                "warehouse_code": "RENO",
                "initial_available": 100,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_reno.status_code == 201
        reno_inv = res_reno.json()
        assert reno_inv["available_quantity"] == 100
        assert reno_inv["warehouse_code"] == "RENO"
        reno_inv_id = reno_inv["id"]

        # Attempt duplicate creation for Product + RENO -> 409 Conflict
        res_dup = await client.post(
            "/v1/inventory",
            json={
                "product_id": product.id,
                "warehouse_code": "RENO",
                "initial_available": 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dup.status_code == 409

        # Create Inventory for Product + COLUMBUS -> 201 Created (Warehouse isolation)
        res_col = await client.post(
            "/v1/inventory",
            json={
                "product_id": product.id,
                "warehouse_code": "COLUMBUS",
                "initial_available": 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_col.status_code == 201
        col_inv = res_col.json()
        assert col_inv["available_quantity"] == 50
        assert col_inv["warehouse_code"] == "COLUMBUS"


@pytest.mark.asyncio
async def test_inventory_adjustment_and_movement_logging():
    """Verifies stock adjustment delta (+10, -15), signed quantity movement log creation, and user tracking."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Adjust Test",
        email="adjusttest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    # Setup Product and RENO Inventory
    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="ADJ_SELLER", name="Adj Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="ADJ-SKU-200", name="Adjustment Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create RENO Inventory (available=50)
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 50},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        # Positive adjustment (+10) -> available becomes 60
        res_adj1 = await client.patch(
            f"/v1/inventory/{inv_id}/adjust",
            json={"quantity_delta": 10, "note": "Cycle count addition"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_adj1.status_code == 200
        assert res_adj1.json()["available_quantity"] == 60

        # Negative adjustment (-15) -> available becomes 45
        res_adj2 = await client.patch(
            f"/v1/inventory/{inv_id}/adjust",
            json={"quantity_delta": -15, "note": "Damaged stock removal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_adj2.status_code == 200
        assert res_adj2.json()["available_quantity"] == 45

        # Verify historical InventoryMovement log entries
        res_mov = await client.get(
            f"/v1/inventory/{inv_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_mov.status_code == 200
        movements = res_mov.json()
        assert len(movements) == 2
        assert movements[0]["quantity"] == -15  # Most recent first
        assert movements[0]["user_id"] == created_admin.id
        assert movements[1]["quantity"] == 10


@pytest.mark.asyncio
async def test_inventory_invariant_negative_quantity_rejection():
    """Verifies that an adjustment resulting in negative stock is rejected with HTTP 400 and leaves database stock untouched."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Invariant Test",
        email="invarianttest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="INV_VAR_SELLER", name="Var Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="INV-VAR-300", name="Invariant Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        # Adjustment -15 on available=10 -> HTTP 400 Bad Request
        res_bad = await client.patch(
            f"/v1/inventory/{inv_id}/adjust",
            json={"quantity_delta": -15, "note": "Excessive removal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_bad.status_code == 400
        assert "Insufficient stock" in res_bad.json()["detail"]

        # Verify stock remains unchanged at 10
        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_check.status_code == 200
        assert res_check.json()["available_quantity"] == 10


@pytest.mark.asyncio
async def test_inventory_invalid_warehouse_rejection():
    """Verifies that creating inventory for a non-existent warehouse code returns HTTP 404 Not Found."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Test",
        email="badwh@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="BAD_WH_SELLER", name="Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="BAD-WH-SKU", name="Bad Warehouse SKU", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "INVALID_WH", "initial_available": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
