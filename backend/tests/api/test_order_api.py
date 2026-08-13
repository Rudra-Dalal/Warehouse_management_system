import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.database.database import DatabaseManager
from core.models.inventory_model import InventoryModel
from core.models.product_model import ProductModel
from core.models.role_model import RoleModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_successful_order_creation_and_reservation():
    """Test creating a single-item customer order.
    Initial stock: available=20, reserved=0.
    Order quantity: 5.
    Asserts: HTTP 200 OK, status="CONFIRMED", available=15, reserved=5, RESERVATION movement created.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Order Test Admin",
            email="order_admin1@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="ORDER_SELLER_1", name="Order Seller 1")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="ORD-SKU-100", name="Order Product 1", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=20,
            reserved_quantity=0,
            damaged_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-TEST-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["order_number"] == "ORD-TEST-001"
        assert data["status"] == "CONFIRMED"
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 5

        # Verify DB stock state
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 15
        assert updated_inv.reserved_quantity == 5

        # Verify Movement log with linked reference_id
        mov_crud = InventoryMovementCRUD()
        movements = await mov_crud.list_movements_by_context(product.id, reno_id)
        assert len(movements) == 1
        assert movements[0].movement_type == "RESERVATION"
        assert movements[0].quantity == -5
        assert movements[0].reference_type == "ORDER"
        assert movements[0].reference_id == data["id"]


@pytest.mark.asyncio
async def test_multi_item_order_atomic_reservation():
    """Test creating a multi-product order where both products have sufficient stock."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Multi Order Admin",
            email="multi_order_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="MULTI_SELLER", name="Multi Seller")
    )

    product_crud = ProductCRUD()
    prod_a = await product_crud.create_product(
        ProductModel(sku="MULTI-SKU-A", name="Product A", seller_id=seller.id)
    )
    prod_b = await product_crud.create_product(
        ProductModel(sku="MULTI-SKU-B", name="Product B", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    columbus = await db["warehouses"].find_one({"code": "COLUMBUS"})
    col_id = str(columbus["_id"])

    inv_crud = InventoryCRUD()
    await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_a.id,
            warehouse_id=col_id,
            available_quantity=100,
            reserved_quantity=0,
        )
    )
    await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_b.id,
            warehouse_id=col_id,
            available_quantity=50,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-MULTI-001",
                "seller_id": seller.id,
                "warehouse_code": "COLUMBUS",
                "items": [
                    {"product_id": prod_a.id, "quantity": 10},
                    {"product_id": prod_b.id, "quantity": 20},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200

        inv_a = await inv_crud.get_by_product_and_warehouse(prod_a.id, col_id)
        assert inv_a.available_quantity == 90
        assert inv_a.reserved_quantity == 10

        inv_b = await inv_crud.get_by_product_and_warehouse(prod_b.id, col_id)
        assert inv_b.available_quantity == 30
        assert inv_b.reserved_quantity == 20


@pytest.mark.asyncio
async def test_multi_item_partial_failure_all_or_nothing():
    """Test all-or-nothing atomicity when Product A (100 available) succeeds but Product B (2 available) fails (5 requested).
    Asserts: HTTP 409 Conflict. Zero items reserved! Product A available stock remains 100!
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Partial Order Admin",
            email="partial_order_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="PARTIAL_SELLER", name="Partial Seller")
    )

    product_crud = ProductCRUD()
    prod_a = await product_crud.create_product(
        ProductModel(sku="PARTIAL-SKU-A", name="Product A", seller_id=seller.id)
    )
    prod_b = await product_crud.create_product(
        ProductModel(sku="PARTIAL-SKU-B", name="Product B", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_a.id,
            warehouse_id=reno_id,
            available_quantity=100,
            reserved_quantity=0,
        )
    )
    await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_b.id,
            warehouse_id=reno_id,
            available_quantity=2,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-PARTIAL-FAIL-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [
                    {"product_id": prod_a.id, "quantity": 10},
                    {"product_id": prod_b.id, "quantity": 5},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 409

        # Verify Product A was NOT partially reserved!
        inv_a = await inv_crud.get_by_product_and_warehouse(prod_a.id, reno_id)
        assert inv_a.available_quantity == 100
        assert inv_a.reserved_quantity == 0

        # Verify Product B remains unchanged
        inv_b = await inv_crud.get_by_product_and_warehouse(prod_b.id, reno_id)
        assert inv_b.available_quantity == 2
        assert inv_b.reserved_quantity == 0


@pytest.mark.asyncio
async def test_single_item_insufficient_inventory_409():
    """Test 409 Conflict when requesting more quantity than available for a single item."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Single Insuff Admin",
            email="single_insuff_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="SINGLE_INSUFF_SELLER", name="Single Insuff Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="SINGLE-INSUFF-SKU", name="Single Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=5,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-SINGLE-INSUFF-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 10}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 409

        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 5
        assert updated_inv.reserved_quantity == 0


@pytest.mark.asyncio
async def test_order_idempotency():
    """Test that submitting an identical order_number twice returns the existing order (HTTP 200) without double reserving stock."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Idem Order Admin",
            email="idem_order_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="IDEM_ORD_SELLER", name="Idem Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="IDEM-ORD-SKU", name="Idem Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=20,
            reserved_quantity=0,
        )
    )

    payload = {
        "order_number": "ORD-IDEM-001",
        "seller_id": seller.id,
        "warehouse_code": "RENO",
        "items": [{"product_id": product.id, "quantity": 10}],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Request 1
        res1 = await client.post(
            "/v1/orders",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200
        order_id1 = res1.json()["id"]

        # Request 2 (Duplicate order_number)
        res2 = await client.post(
            "/v1/orders",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 200
        assert res2.json()["id"] == order_id1

        # Stock must be reserved ONLY ONCE (available=10, reserved=10)
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 10
        assert updated_inv.reserved_quantity == 10


@pytest.mark.asyncio
async def test_duplicate_order_different_payload():
    """Test that submitting an existing order_number with a different payload returns the original order without reserving again."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Diff Idem Admin",
            email="diff_idem_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="DIFF_IDEM_SELLER", name="Diff Idem Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="DIFF-IDEM-SKU", name="Diff Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=100,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Initial submission (qty 10)
        res1 = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-DIFF-PAYLOAD-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 10}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200

        # Duplicate order_number with different payload (qty 50)
        res2 = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-DIFF-PAYLOAD-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 50}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 200
        assert res2.json()["items"][0]["quantity"] == 10

        # Verify stock was reserved ONLY for original request (available=90, reserved=10)
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 90
        assert updated_inv.reserved_quantity == 10


@pytest.mark.asyncio
async def test_missing_inventory_record_404():
    """Test 404 Not Found when product exists but no inventory record is registered for the target warehouse."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Missing Inv Admin",
            email="missing_inv_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="MISSING_INV_SELLER", name="Missing Inv Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="MISSING-INV-SKU", name="Missing Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-MISSING-INV-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
        assert "Inventory record not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_validation_errors_404_and_422():
    """Test 404 Not Found for non-existent seller/warehouse/product and 422 for invalid quantity."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Val Error Admin",
            email="val_err_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="VAL_SELLER", name="Val Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="VAL-SKU-100", name="Val Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid Seller (404)
        res_seller = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-INVALID-SELLER",
                "seller_id": "60d5ec49f1b2c8b1f8c1e999",
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_seller.status_code == 404

        # Invalid Warehouse Code (404)
        res_wh = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-INVALID-WH",
                "seller_id": seller.id,
                "warehouse_code": "INVALID_WH",
                "items": [{"product_id": product.id, "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_wh.status_code == 404

        # Invalid Product ID (404)
        res_prod = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-INVALID-PROD",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": "60d5ec49f1b2c8b1f8c1e888", "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_prod.status_code == 404

        # Invalid Quantity <= 0 (422)
        res_qty = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-INVALID-QTY",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 0}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_qty.status_code == 422

        # Empty items list (422)
        res_empty = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-EMPTY-ITEMS",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_empty.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_and_unauthorized_access():
    """Test 401 Unauthorized for unauthenticated requests and 403 Forbidden for users lacking orders permissions."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Unauthenticated request (401)
        res_unauth = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-UNAUTH-001",
                "seller_id": "60d5ec49f1b2c8b1f8c1e001",
                "warehouse_code": "RENO",
                "items": [{"product_id": "60d5ec49f1b2c8b1f8c1e003", "quantity": 1}],
            },
        )
        assert res_unauth.status_code == 401

        # User without orders permissions (403)
        role_crud = RoleCRUD()
        empty_role = await role_crud.create_role(
            RoleModel(name="EMPTY_ORDER_ROLE", description="Role with no permissions", permission_ids=[])
        )

        user_crud = UserCRUD()
        unauth_user = await user_crud.create_user(
            UserModel(
                name="Forbidden Order User",
                email="forbidden_order_user@example.com",
                password_hash=hash_password("Pass123!"),
                role_id=empty_role.id,
                is_active=True,
            )
        )
        forbidden_token = create_access_token(subject=unauth_user.id)

        res_forbidden = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-FORBIDDEN-001",
                "seller_id": "60d5ec49f1b2c8b1f8c1e001",
                "warehouse_code": "RENO",
                "items": [{"product_id": "60d5ec49f1b2c8b1f8c1e003", "quantity": 1}],
            },
            headers={"Authorization": f"Bearer {forbidden_token}"},
        )
        assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_order_retrieval_and_listing():
    """Test GET /v1/orders and GET /v1/orders/{order_id}."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Get Order Admin",
            email="get_order_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="GET_ORD_SELLER", name="Get Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="GET-ORD-SKU", name="Get Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=20,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_res = await client.post(
            "/v1/orders",
            json={
                "order_number": "ORD-GET-API-001",
                "seller_id": seller.id,
                "warehouse_code": "RENO",
                "items": [{"product_id": product.id, "quantity": 5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_res.status_code == 200
        order_id = create_res.json()["id"]

        # GET /v1/orders/{order_id}
        get_res = await client.get(
            f"/v1/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["order_number"] == "ORD-GET-API-001"

        # GET /v1/orders?warehouse_code=RENO
        list_res = await client.get(
            "/v1/orders?warehouse_code=RENO",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1
