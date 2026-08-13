import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.models.product_model import ProductModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_successful_receiving():
    """Verifies successful receiving increases available stock and logs a RECEIVING movement."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Rec Test",
        email="rec_admin@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="REC_SELLER_1", name="Rec Seller 1"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="REC-SKU-100", name="Receiving Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Receive 100 units at RENO
        payload = {
            "receiving_reference": "WH-REC-001",
            "warehouse_code": "RENO",
            "seller_id": seller.id,
            "items": [{"product_id": product.id, "quantity": 100}],
        }
        res = await client.post(
            "/v1/receiving",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        rec_data = res.json()
        assert rec_data["receiving_reference"] == "WH-REC-001"
        assert rec_data["status"] == "RECEIVED"
        assert len(rec_data["items"]) == 1
        assert rec_data["items"][0]["quantity"] == 100

        # Verify inventory created with available_quantity=100
        res_inv = await client.get(
            f"/v1/inventory?product_id={product.id}&warehouse_code=RENO",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_inv.status_code == 200
        inv_list = res_inv.json()
        assert len(inv_list) == 1
        inv = inv_list[0]
        assert inv["available_quantity"] == 100
        assert inv["reserved_quantity"] == 0

        # Verify RECEIVING movement created (+100)
        mov_crud = InventoryMovementCRUD()
        movements = await mov_crud.list_movements_by_context(product.id, inv["warehouse_id"])
        assert len(movements) == 1
        assert movements[0].movement_type == "RECEIVING"
        assert movements[0].quantity == 100
        assert movements[0].user_id == created_admin.id


@pytest.mark.asyncio
async def test_duplicate_receiving_idempotency():
    """Verifies that submitting the same receiving reference again returns the existing result without double-counting stock."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Dup Rec Test",
        email="rec_dup@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="REC_DUP_SELLER", name="Dup Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="REC-DUP-SKU", name="Dup Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "receiving_reference": "WH-REC-DUP-001",
            "warehouse_code": "RENO",
            "seller_id": seller.id,
            "items": [{"product_id": product.id, "quantity": 100}],
        }
        # First submission
        res1 = await client.post(
            "/v1/receiving",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200

        # Second submission (Idempotent retry)
        res2 = await client.post(
            "/v1/receiving",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 200
        assert res2.json()["id"] == res1.json()["id"]

        # Verify stock remains 100 (NOT 200)
        res_inv = await client.get(
            f"/v1/inventory?product_id={product.id}&warehouse_code=RENO",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_inv.json()[0]["available_quantity"] == 100

        # Verify only 1 movement log exists
        mov_crud = InventoryMovementCRUD()
        inv_id = res_inv.json()[0]["warehouse_id"]
        movements = await mov_crud.list_movements_by_context(product.id, inv_id)
        assert len(movements) == 1


@pytest.mark.asyncio
async def test_duplicate_receiving_different_payload():
    """Verifies that submitting a duplicate reference with a different payload (e.g. 500 units at COLUMBUS) returns the original result."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Diff Payload",
        email="rec_diff@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="REC_DIFF_SELLER", name="Diff Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="REC-DIFF-SKU", name="Diff Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Original submission: WH-REC-DIFF at RENO for 100 units
        res1 = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-DIFF",
                "warehouse_code": "RENO",
                "seller_id": seller.id,
                "items": [{"product_id": product.id, "quantity": 100}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200

        # Altered submission with same receiving_reference at COLUMBUS for 500 units
        res2 = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-DIFF",
                "warehouse_code": "COLUMBUS",
                "seller_id": seller.id,
                "items": [{"product_id": product.id, "quantity": 500}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 200
        # Returns original RENO receiving shipment
        assert res2.json()["id"] == res1.json()["id"]

        # COLUMBUS inventory remains empty
        res_col = await client.get(
            f"/v1/inventory?product_id={product.id}&warehouse_code=COLUMBUS",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(res_col.json()) == 0


@pytest.mark.asyncio
async def test_validation_errors():
    """Verifies 404 for unknown seller, warehouse, or product, and 422 for invalid quantities."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Val Test",
        email="rec_val@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="REC_VAL_SELLER", name="Val Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="REC-VAL-SKU", name="Val Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid seller -> 404
        res_seller = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-VAL-1",
                "warehouse_code": "RENO",
                "seller_id": "65c3b1a2f91a2b3c4d5e6f7a",
                "items": [{"product_id": product.id, "quantity": 10}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_seller.status_code == 404

        # Invalid warehouse -> 404
        res_wh = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-VAL-2",
                "warehouse_code": "INVALID_WH",
                "seller_id": seller.id,
                "items": [{"product_id": product.id, "quantity": 10}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_wh.status_code == 404

        # Invalid product -> 404
        res_prod = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-VAL-3",
                "warehouse_code": "RENO",
                "seller_id": seller.id,
                "items": [{"product_id": "65c3b1a2f91a2b3c4d5e6f7a", "quantity": 10}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_prod.status_code == 404

        # Quantity 0 -> 422
        res_qty0 = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-VAL-4",
                "warehouse_code": "RENO",
                "seller_id": seller.id,
                "items": [{"product_id": product.id, "quantity": 0}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_qty0.status_code == 422


@pytest.mark.asyncio
async def test_multi_product_receiving():
    """Verifies single receiving shipment with multiple line items updates each inventory record correctly."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Multi Prod",
        email="rec_multi@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="REC_MULTI_SELLER", name="Multi Seller"))

    product_crud = ProductCRUD()
    p1 = await product_crud.create_product(ProductModel(sku="REC-M-SKU-1", name="Item 1", seller_id=seller.id))
    p2 = await product_crud.create_product(ProductModel(sku="REC-M-SKU-2", name="Item 2", seller_id=seller.id))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/receiving",
            json={
                "receiving_reference": "WH-REC-MULTI-001",
                "warehouse_code": "RENO",
                "seller_id": seller.id,
                "items": [
                    {"product_id": p1.id, "quantity": 100},
                    {"product_id": p2.id, "quantity": 50},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert len(res.json()["items"]) == 2

        # Verify P1 stock = 100
        res_p1 = await client.get(
            f"/v1/inventory?product_id={p1.id}&warehouse_code=RENO",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_p1.json()[0]["available_quantity"] == 100

        # Verify P2 stock = 50
        res_p2 = await client.get(
            f"/v1/inventory?product_id={p2.id}&warehouse_code=RENO",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_p2.json()[0]["available_quantity"] == 50
