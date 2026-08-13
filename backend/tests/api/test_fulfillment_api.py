import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.fulfillment_crud import FulfillmentCRUD
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.permission_crud import PermissionCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.database.database import DatabaseManager
from core.models.inventory_model import InventoryModel
from core.models.order_model import OrderItemModel, OrderModel
from core.models.product_model import ProductModel
from core.models.role_model import RoleModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


async def setup_fulfillment_fixtures():
    """Sets up RBAC user, seller, warehouse, product, inventory, and confirmed order fixtures."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")
    perm_crud = PermissionCRUD()
    perms = await perm_crud.get_by_ids(admin_role.permission_ids)
    print("\nDEBUG ADMIN PERMS:", [p.name for p in perms])

    user_crud = UserCRUD()
    user = await user_crud.create_user(
        UserModel(
            name="Fulfillment Tester",
            email="fulfillment_test_user@example.com",
            password_hash=hash_password("Pass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="FULFILL_SELLER_1", name="Fulfillment Seller")
    )

    product_crud = ProductCRUD()
    product_a = await product_crud.create_product(
        ProductModel(sku="FULFILL-SKU-A", name="Product Alpha", seller_id=seller.id)
    )
    product_b = await product_crud.create_product(
        ProductModel(sku="FULFILL-SKU-B", name="Product Beta", seller_id=seller.id)
    )

    db = DatabaseManager.get_db()
    reno = await db["warehouses"].find_one({"code": "RENO"})
    reno_id = str(reno["_id"])

    inv_crud = InventoryCRUD()
    # Available = 90, Reserved = 10 (reserved via order creation)
    inv_a = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product_a.id,
            warehouse_id=reno_id,
            available_quantity=90,
            reserved_quantity=10,
        )
    )
    inv_b = await inv_crud.create_inventory(
        InventoryModel(
            product_id=product_b.id,
            warehouse_id=reno_id,
            available_quantity=50,
            reserved_quantity=5,
        )
    )

    # Confirmed Order
    order_crud = OrderCRUD()
    confirmed_order = await order_crud.create_order(
        OrderModel(
            order_number="ORD-FULFILL-001",
            seller_id=seller.id,
            warehouse_id=reno_id,
            status="CONFIRMED",
            items=[
                OrderItemModel(product_id=product_a.id, quantity=10),
                OrderItemModel(product_id=product_b.id, quantity=5),
            ],
            created_by_user_id=user.id,
        )
    )

    return {
        "user": user,
        "headers": headers,
        "seller": seller,
        "product_a": product_a,
        "product_b": product_b,
        "reno_id": reno_id,
        "inv_a": inv_a,
        "inv_b": inv_b,
        "confirmed_order": confirmed_order,
    }


@pytest.mark.asyncio
async def test_fulfillment_creation_lifecycle():
    """Tests fulfillment creation from confirmed order, 404 for nonexistent order, and 409 for non-confirmed order."""
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Nonexistent order -> 404
        resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": "60f1a2b3c4d5e6f7a8b9c0d1"},
            headers=fx["headers"],
        )
        assert resp.status_code == 404

        # 2. Successful creation from confirmed order -> 201
        resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["order_id"] == fx["confirmed_order"].id
        assert data["order_number"] == "ORD-FULFILL-001"
        assert data["status"] == "READY_TO_PICK"
        assert len(data["items"]) == 2

        # 3. Idempotent duplicate creation -> 200 or 201 (returns existing fulfillment)
        resp_dup = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        assert resp_dup.status_code in (200, 201)
        assert resp_dup.json()["id"] == data["id"]

        # 4. Attempt creation from non-confirmed order -> 409
        order_crud = OrderCRUD()
        unconfirmed_order = await order_crud.create_order(
            OrderModel(
                order_number="ORD-PENDING-99",
                seller_id=fx["seller"].id,
                warehouse_id=fx["reno_id"],
                status="PENDING",
                items=[OrderItemModel(product_id=fx["product_a"].id, quantity=1)],
                created_by_user_id=fx["user"].id,
            )
        )
        resp_unconf = await client.post(
            "/v1/fulfillment",
            json={"order_id": unconfirmed_order.id},
            headers=fx["headers"],
        )
        print("\nDEBUG UNCONF STATUS:", resp_unconf.status_code, resp_unconf.text)
        assert resp_unconf.status_code == 409


@pytest.mark.asyncio
async def test_fulfillment_retrieval_and_listing():
    """Tests fulfillment retrieval by ID and listing by warehouse and status."""
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create fulfillment
        create_resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        ful_id = create_resp.json()["id"]

        # Get by ID
        get_resp = await client.get(f"/v1/fulfillment/{ful_id}", headers=fx["headers"])
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == ful_id

        # Nonexistent ID -> 404
        get_404 = await client.get("/v1/fulfillment/60f1a2b3c4d5e6f7a8b9c0d1", headers=fx["headers"])
        assert get_404.status_code == 404

        # List fulfillments
        list_resp = await client.get("/v1/fulfillment?warehouse_code=RENO&status=READY_TO_PICK", headers=fx["headers"])
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) >= 1
        assert any(i["id"] == ful_id for i in items)


@pytest.mark.asyncio
async def test_successful_pick_and_inventory_semantics():
    """CRITICAL TEST: Verifies that picking stock:
    1. Decrements reserved_quantity from 10 to 0.
    2. DOES NOT decrement available_quantity again (remains 90).
    3. Records a PICK inventory movement.
    4. Is idempotent (repeated pick returns current state without double-consuming).
    """
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create fulfillment
        create_resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        ful_id = create_resp.json()["id"]

        # Perform complete pick
        pick_payload = {
            "items": [
                {"product_id": fx["product_a"].id, "quantity": 10},
                {"product_id": fx["product_b"].id, "quantity": 5},
            ]
        }
        pick_resp = await client.post(
            f"/v1/fulfillment/{ful_id}/pick",
            json=pick_payload,
            headers=fx["headers"],
        )
        assert pick_resp.status_code == 200
        pdata = pick_resp.json()
        assert pdata["status"] == "PICKED"
        assert pdata["picked_by_user_id"] == fx["user"].id
        assert pdata["picked_at"] is not None

        # Verify Inventory state
        inv_crud = InventoryCRUD()
        updated_inv_a = await inv_crud.get_by_id(fx["inv_a"].id)
        # CRITICAL ASSERTION: available_quantity MUST REMAIN 90! reserved_quantity MUST BE 0!
        assert updated_inv_a.available_quantity == 90
        assert updated_inv_a.reserved_quantity == 0

        updated_inv_b = await inv_crud.get_by_id(fx["inv_b"].id)
        assert updated_inv_b.available_quantity == 50
        assert updated_inv_b.reserved_quantity == 0

        # Verify Inventory Movement logs
        mov_crud = InventoryMovementCRUD()
        movements_a = await mov_crud.list_movements_by_context(fx["product_a"].id, fx["reno_id"])
        pick_movs_a = [m for m in movements_a if m.movement_type == "PICK"]
        assert len(pick_movs_a) == 1
        assert pick_movs_a[0].quantity == -10
        assert pick_movs_a[0].reference_type == "FULFILLMENT"
        assert pick_movs_a[0].reference_id == ful_id

        # Idempotent re-pick -> 200 OK without double decrementing stock
        pick_dup_resp = await client.post(
            f"/v1/fulfillment/{ful_id}/pick",
            json=pick_payload,
            headers=fx["headers"],
        )
        assert pick_dup_resp.status_code == 200
        # Re-check stock: available stays 90, reserved stays 0
        recheck_inv_a = await inv_crud.get_by_id(fx["inv_a"].id)
        assert recheck_inv_a.available_quantity == 90
        assert recheck_inv_a.reserved_quantity == 0


@pytest.mark.asyncio
async def test_full_fulfillment_lifecycle_pick_pack_ship():
    """Tests full execution lifecycle: CONFIRMED -> READY_TO_PICK -> PICKED -> PACKED -> SHIPPED.

    Verifies final order.status = SHIPPED and fulfillment.status = SHIPPED.
    """
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Fulfillment
        create_resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        ful_id = create_resp.json()["id"]

        # 2. Attempt PACK before PICK -> 409 Conflict
        pack_early = await client.post(f"/v1/fulfillment/{ful_id}/pack", json={}, headers=fx["headers"])
        assert pack_early.status_code == 409

        # 3. Attempt SHIP before PACK -> 409 Conflict
        ship_early = await client.post(f"/v1/fulfillment/{ful_id}/ship", json={}, headers=fx["headers"])
        assert ship_early.status_code == 409

        # 4. PICK -> status = PICKED
        pick_resp = await client.post(
            f"/v1/fulfillment/{ful_id}/pick",
            json={
                "items": [
                    {"product_id": fx["product_a"].id, "quantity": 10},
                    {"product_id": fx["product_b"].id, "quantity": 5},
                ]
            },
            headers=fx["headers"],
        )
        assert pick_resp.status_code == 200
        assert pick_resp.json()["status"] == "PICKED"

        # 5. PACK -> status = PACKED
        pack_resp = await client.post(
            f"/v1/fulfillment/{ful_id}/pack",
            json={"note": "Fragile items packed carefully"},
            headers=fx["headers"],
        )
        assert pack_resp.status_code == 200
        pack_data = pack_resp.json()
        assert pack_data["status"] == "PACKED"
        assert pack_data["packed_by_user_id"] == fx["user"].id
        assert pack_data["packed_at"] is not None

        # Idempotent repeat pack -> 200
        pack_dup = await client.post(f"/v1/fulfillment/{ful_id}/pack", json={}, headers=fx["headers"])
        assert pack_dup.status_code == 200

        # 6. SHIP -> status = SHIPPED (updates fulfillment AND order status to SHIPPED)
        ship_resp = await client.post(
            f"/v1/fulfillment/{ful_id}/ship",
            json={"tracking_number": "TRACK-WHIT-12345"},
            headers=fx["headers"],
        )
        assert ship_resp.status_code == 200
        ship_data = ship_resp.json()
        assert ship_data["status"] == "SHIPPED"
        assert ship_data["shipped_by_user_id"] == fx["user"].id
        assert ship_data["shipped_at"] is not None

        # Verify Order status in DB is now SHIPPED
        order_crud = OrderCRUD()
        final_order = await order_crud.get_by_id(fx["confirmed_order"].id)
        assert final_order.status == "SHIPPED"

        # Idempotent repeat ship -> 200
        ship_dup = await client.post(f"/v1/fulfillment/{ful_id}/ship", json={}, headers=fx["headers"])
        assert ship_dup.status_code == 200


@pytest.mark.asyncio
async def test_invalid_pick_validation_and_atomicity():
    """Tests validation errors (incomplete pick quantity) and atomicity rollback when pick fails."""
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=fx["headers"],
        )
        ful_id = create_resp.json()["id"]

        # Incomplete pick (Product A ordered 10, picked 5) -> 422 Unprocessable Entity
        bad_pick = await client.post(
            f"/v1/fulfillment/{ful_id}/pick",
            json={
                "items": [
                    {"product_id": fx["product_a"].id, "quantity": 5},
                    {"product_id": fx["product_b"].id, "quantity": 5},
                ]
            },
            headers=fx["headers"],
        )
        assert bad_pick.status_code == 422

        # Verify zero stock changes took place
        inv_crud = InventoryCRUD()
        check_inv_a = await inv_crud.get_by_id(fx["inv_a"].id)
        assert check_inv_a.reserved_quantity == 10

        # Verify zero PICK movements logged
        mov_crud = InventoryMovementCRUD()
        movs = await mov_crud.list_movements_by_context(fx["product_a"].id, fx["reno_id"])
        pick_movs = [m for m in movs if m.movement_type == "PICK"]
        assert len(pick_movs) == 0


@pytest.mark.asyncio
async def test_fulfillment_rbac_permissions():
    """Tests authentication (401) and authorization RBAC permission enforcement (403)."""
    fx = await setup_fulfillment_fixtures()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        unauth = await client.get("/v1/fulfillment")
        assert unauth.status_code == 401

        # 2. User lacking fulfillment permissions -> 403
        role_crud = RoleCRUD()
        # Create custom role with ZERO permissions
        empty_role = await role_crud.create_role(
            RoleModel(name="RESTRICTED_ROLE", description="No perms", permission_ids=[])
        )
        user_crud = UserCRUD()
        restricted_user = await user_crud.create_user(
            UserModel(
                name="Restricted Worker",
                email="restricted_worker@example.com",
                password_hash=hash_password("Pass123!"),
                role_id=empty_role.id,
                is_active=True,
            )
        )
        bad_token = create_access_token(subject=restricted_user.id)
        bad_headers = {"Authorization": f"Bearer {bad_token}"}

        forbidden_create = await client.post(
            "/v1/fulfillment",
            json={"order_id": fx["confirmed_order"].id},
            headers=bad_headers,
        )
        assert forbidden_create.status_code == 403

        forbidden_list = await client.get("/v1/fulfillment", headers=bad_headers)
        assert forbidden_list.status_code == 403
