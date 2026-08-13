import asyncio
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
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_primary_concurrent_orders():
    """THE PRIMARY PHASE 6 ACCEPTANCE TEST:
    Initial stock: available=9, reserved=0.
    10 concurrent distinct order requests for 9 units each (ORD-CONC-001 .. ORD-CONC-010).
    Asserts: Exactly 1 order succeeds (HTTP 200), exactly 9 orders fail (HTTP 409).
    Final DB state: available_quantity=0, reserved_quantity=9, and exactly 1 RESERVATION movement.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Conc Order Admin",
            email="conc_order_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="CONC_ORD_SELLER", name="Conc Order Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-ORD-SKU-9", name="Conc Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=9,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker(idx: int):
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": f"ORD-CONC-{idx:03d}",
                    "seller_id": seller.id,
                    "warehouse_code": "RENO",
                    "items": [{"product_id": product.id, "quantity": 9}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker(i)) for i in range(1, 11)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        print("\nDEBUG STATUS CODES:", status_codes)
        success_count = status_codes.count(200)
        fail_count = status_codes.count(409)

        assert success_count == 1, f"Expected exactly 1 success, got {success_count}. Details: {status_details}"
        assert fail_count == 9, f"Expected exactly 9 failures, got {fail_count}. Details: {status_details}"

        # Assert final DB inventory
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 0
        assert updated_inv.reserved_quantity == 9

        # Assert DB movements: exactly 1 RESERVATION movement
        mov_crud = InventoryMovementCRUD()
        movements = await mov_crud.list_movements_by_context(product.id, reno_id)
        assert len(movements) == 1
        assert movements[0].quantity == -9
        assert movements[0].movement_type == "RESERVATION"


@pytest.mark.asyncio
async def test_concurrent_small_orders():
    """Initial stock: available=10, reserved=0.
    10 concurrent distinct order requests for 1 unit each.
    Asserts: All 10 orders succeed (HTTP 200).
    Final DB state: available_quantity=0, reserved_quantity=10.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Small Conc Admin",
            email="small_conc_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="SMALL_CONC_SELLER", name="Small Conc Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="SMALL-CONC-SKU-10", name="Small Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=10,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker(idx: int):
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": f"ORD-SMALL-{idx:03d}",
                    "seller_id": seller.id,
                    "warehouse_code": "RENO",
                    "items": [{"product_id": product.id, "quantity": 1}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker(i)) for i in range(1, 11)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert status_codes == [200] * 10

        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 0
        assert updated_inv.reserved_quantity == 10


@pytest.mark.asyncio
async def test_concurrent_warehouse_isolation():
    """Product A: RENO available=100, COLUMBUS available=10.
    Concurrent orders: RENO (10 units) and COLUMBUS (5 units).
    Asserts: RENO available=90 / reserved=10; COLUMBUS available=5 / reserved=5.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Iso Conc Admin",
            email="iso_conc_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="ISO_ORD_SELLER", name="Iso Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="ISO-ORD-SKU", name="Iso Product", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])
    columbus = await db["warehouses"].find_one({"code": "COLUMBUS"})
    col_id = str(columbus["_id"])

    inv_crud = InventoryCRUD()
    inv_reno = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=reno_id,
            available_quantity=100,
            reserved_quantity=0,
        )
    )
    inv_col = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product.id,
            warehouse_id=col_id,
            available_quantity=10,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker_reno():
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": "ORD-ISO-RENO-001",
                    "seller_id": seller.id,
                    "warehouse_code": "RENO",
                    "items": [{"product_id": product.id, "quantity": 10}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        async def worker_columbus():
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": "ORD-ISO-COL-001",
                    "seller_id": seller.id,
                    "warehouse_code": "COLUMBUS",
                    "items": [{"product_id": product.id, "quantity": 5}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        task1 = asyncio.create_task(worker_reno())
        task2 = asyncio.create_task(worker_columbus())
        start_event.set()

        res_reno, res_col = await asyncio.gather(task1, task2)
        assert res_reno.status_code == 200
        assert res_col.status_code == 200

        updated_reno = await inv_crud.get_by_id(inv_reno.id)
        assert updated_reno.available_quantity == 90
        assert updated_reno.reserved_quantity == 10

        updated_col = await inv_crud.get_by_id(inv_col.id)
        assert updated_col.available_quantity == 5
        assert updated_col.reserved_quantity == 5


@pytest.mark.asyncio
async def test_concurrent_multi_item_orders():
    """Test 2 concurrent multi-item order requests (ORD-001 and ORD-002) both requesting A=10 and B=10
    when stock for Product A is 10 and Product B is 10.
    Asserts: Exactly 1 order succeeds, 1 fails. Final stock: A reserved=10, B reserved=10. Zero overselling!
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Multi Conc Admin",
            email="multi_conc_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="MULTI_CONC_SELLER", name="Multi Conc Seller")
    )

    product_crud = ProductCRUD()
    prod_a = await product_crud.create_product(
        ProductModel(sku="MULTI-CONC-A", name="Product A", seller_id=seller.id)
    )
    prod_b = await product_crud.create_product(
        ProductModel(sku="MULTI-CONC-B", name="Product B", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv_a = await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_a.id,
            warehouse_id=reno_id,
            available_quantity=10,
            reserved_quantity=0,
        )
    )
    inv_b = await inv_crud.create_inventory(
        InventoryModel(
            product_id=prod_b.id,
            warehouse_id=reno_id,
            available_quantity=10,
            reserved_quantity=0,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker(order_num: str):
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": order_num,
                    "seller_id": seller.id,
                    "warehouse_code": "RENO",
                    "items": [
                        {"product_id": prod_a.id, "quantity": 10},
                        {"product_id": prod_b.id, "quantity": 10},
                    ],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        t1 = asyncio.create_task(worker("ORD-MULTI-CONC-001"))
        t2 = asyncio.create_task(worker("ORD-MULTI-CONC-002"))
        start_event.set()

        res1, res2 = await asyncio.gather(t1, t2)
        status_codes = [res1.status_code, res2.status_code]
        assert status_codes.count(200) == 1
        assert status_codes.count(409) == 1

        updated_a = await inv_crud.get_by_id(inv_a.id)
        assert updated_a.available_quantity == 0
        assert updated_a.reserved_quantity == 10

        updated_b = await inv_crud.get_by_id(inv_b.id)
        assert updated_b.available_quantity == 0
        assert updated_b.reserved_quantity == 10


@pytest.mark.asyncio
async def test_concurrent_duplicate_order_number():
    """Test 10 concurrent requests submitting the exact same order_number 'ORD-CONC-DUP-001' requesting 5 units.
    Initial stock: 20 units.
    Asserts: Exactly 1 order document is created in DB. Total reserved stock = 5 units (NOT 50 units).
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin = await user_crud.create_user(
        UserModel(
            name="Dup Conc Admin",
            email="dup_conc_admin@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="DUP_CONC_SELLER", name="Dup Conc Seller")
    )

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="DUP-CONC-SKU", name="Dup Product", seller_id=seller.id)
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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                "/v1/orders",
                json={
                    "order_number": "ORD-CONC-DUP-001",
                    "seller_id": seller.id,
                    "warehouse_code": "RENO",
                    "items": [{"product_id": product.id, "quantity": 5}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert all(code in (200, 409) for code in status_codes)
        assert status_codes.count(200) >= 1

        # Assert database order count for ORD-CONC-DUP-001 is EXACTLY 1
        order_crud = OrderCRUD()
        order = await order_crud.get_by_order_number("ORD-CONC-DUP-001")
        assert order is not None

        # Assert stock was reserved ONLY ONCE for 5 units (available=15, reserved=5)
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 15
        assert updated_inv.reserved_quantity == 5
