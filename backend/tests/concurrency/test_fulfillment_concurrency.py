import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.fulfillment_crud import FulfillmentCRUD
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.database.database import DatabaseManager
from core.models.inventory_model import InventoryModel
from core.models.order_model import OrderItemModel, OrderModel
from core.models.product_model import ProductModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_concurrent_fulfillment_creation():
    """10 concurrent workers attempt to create a fulfillment task for the exact same order.

    Enforced by UNIQUE(order_id) index:
    Asserts: Exactly 1 fulfillment document exists in the database.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    user = await user_crud.create_user(
        UserModel(
            name="Conc Ful Worker",
            email="conc_ful_worker@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_FUL_SELLER", name="Conc Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(ProductModel(sku="CONC-FUL-SKU-1", name="Product Conc", seller_id=seller.id))

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    await inv_crud.create_inventory(
        InventoryModel(product_id=product.id, warehouse_id=reno_id, available_quantity=90, reserved_quantity=10)
    )

    order_crud = OrderCRUD()
    order = await order_crud.create_order(
        OrderModel(
            order_number="ORD-CONC-FUL-001",
            seller_id=seller.id,
            warehouse_id=reno_id,
            status="CONFIRMED",
            items=[OrderItemModel(product_id=product.id, quantity=10)],
            created_by_user_id=user.id,
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                "/v1/fulfillment",
                json={"order_id": order.id},
                headers=headers,
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        # All requests should return 201 (created) or 200 (idempotent result)
        assert all(code in (200, 201) for code in status_codes), f"Unexpected status codes: {status_codes}"

        # Assert exactly 1 fulfillment document in DB for this order
        ful_crud = FulfillmentCRUD()
        ful = await ful_crud.get_by_order_id(order.id)
        assert ful is not None
        assert ful.order_id == order.id

        # Verify DB count is strictly 1
        count = await db["fulfillments"].count_documents({"order_id": order.id})
        assert count == 1


@pytest.mark.asyncio
async def test_concurrent_picking_safety():
    """10 concurrent workers attempt to pick the exact same READY_TO_PICK fulfillment task.

    Asserts:
    1. Reserved quantity is decremented exactly ONCE (from 10 to 0).
    2. Available quantity is NOT decremented again (remains 90).
    3. Exactly 1 PICK movement is created for the product.
    4. Final fulfillment status is PICKED.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    user = await user_crud.create_user(
        UserModel(
            name="Conc Pick Worker",
            email="conc_pick_worker@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_PICK_SELLER", name="Pick Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(ProductModel(sku="CONC-PICK-SKU-1", name="Pick Product", seller_id=seller.id))

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    inv = await inv_crud.create_inventory(
        InventoryModel(product_id=product.id, warehouse_id=reno_id, available_quantity=90, reserved_quantity=10)
    )

    order_crud = OrderCRUD()
    order = await order_crud.create_order(
        OrderModel(
            order_number="ORD-CONC-PICK-001",
            seller_id=seller.id,
            warehouse_id=reno_id,
            status="CONFIRMED",
            items=[OrderItemModel(product_id=product.id, quantity=10)],
            created_by_user_id=user.id,
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create fulfillment
        c_resp = await client.post("/v1/fulfillment", json={"order_id": order.id}, headers=headers)
        ful_id = c_resp.json()["id"]

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/fulfillment/{ful_id}/pick",
                json={"items": [{"product_id": product.id, "quantity": 10}]},
                headers=headers,
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        # Should be 200 OK or 409 Conflict if request payload conflicted during transition
        assert all(code in (200, 409) for code in status_codes), f"Unexpected status codes: {status_codes}"

        # Assert final Inventory State
        updated_inv = await inv_crud.get_by_id(inv.id)
        assert updated_inv.available_quantity == 90
        assert updated_inv.reserved_quantity == 0

        # Assert exactly 1 PICK movement logged
        mov_crud = InventoryMovementCRUD()
        movs = await mov_crud.list_movements_by_context(product.id, reno_id)
        pick_movs = [m for m in movs if m.movement_type == "PICK"]
        assert len(pick_movs) == 1
        assert pick_movs[0].quantity == -10

        # Assert final fulfillment status is PICKED
        ful_crud = FulfillmentCRUD()
        ful = await ful_crud.get_by_id(ful_id)
        assert ful.status.value == "PICKED" if hasattr(ful.status, "value") else ful.status == "PICKED"


@pytest.mark.asyncio
async def test_concurrent_shipping_safety():
    """10 concurrent workers attempt to ship a PACKED fulfillment task.

    Asserts:
    1. Fulfillment status transitions to SHIPPED.
    2. Order status transitions to SHIPPED.
    3. No state corruption or duplicate processing.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    user = await user_crud.create_user(
        UserModel(
            name="Conc Ship Worker",
            email="conc_ship_worker@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SHIP_SELLER", name="Ship Seller"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(ProductModel(sku="CONC-SHIP-SKU-1", name="Ship Product", seller_id=seller.id))

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    await inv_crud.create_inventory(
        InventoryModel(product_id=product.id, warehouse_id=reno_id, available_quantity=90, reserved_quantity=10)
    )

    order_crud = OrderCRUD()
    order = await order_crud.create_order(
        OrderModel(
            order_number="ORD-CONC-SHIP-001",
            seller_id=seller.id,
            warehouse_id=reno_id,
            status="CONFIRMED",
            items=[OrderItemModel(product_id=product.id, quantity=10)],
            created_by_user_id=user.id,
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create, Pick, Pack
        c_resp = await client.post("/v1/fulfillment", json={"order_id": order.id}, headers=headers)
        ful_id = c_resp.json()["id"]

        await client.post(
            f"/v1/fulfillment/{ful_id}/pick",
            json={"items": [{"product_id": product.id, "quantity": 10}]},
            headers=headers,
        )
        await client.post(f"/v1/fulfillment/{ful_id}/pack", json={}, headers=headers)

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/fulfillment/{ful_id}/ship",
                json={"tracking_number": "TRACK-CONC-999"},
                headers=headers,
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert all(code == 200 for code in status_codes), f"Unexpected status codes: {status_codes}"

        # Assert Final Fulfillment & Order Statuses
        ful_crud = FulfillmentCRUD()
        ful = await ful_crud.get_by_id(ful_id)
        assert ful.status.value == "SHIPPED" if hasattr(ful.status, "value") else ful.status == "SHIPPED"

        updated_order = await order_crud.get_by_id(order.id)
        assert updated_order.status == "SHIPPED"
