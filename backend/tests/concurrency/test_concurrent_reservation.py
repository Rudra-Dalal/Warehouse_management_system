import asyncio
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
async def test_primary_concurrency_case():
    """THE CRITICAL BUSINESS CONCURRENCY TEST:
    Initial stock: available=9, reserved=0.
    10 concurrent requests each try to reserve 9 units simultaneously.
    Asserts: Exactly 1 succeeds (200 OK), 9 fail (409 Conflict).
    Final DB state: available=0, reserved=9, 1 RESERVATION movement with quantity=-9.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Primary Concurrency",
        email="prim_conc@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    # Setup Product and Inventory (available=9)
    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SELLER_1", name="Conc Seller 1"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-SKU-9", name="Primary Concurrency Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 9},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/inventory/{inv_id}/reserve",
                json={"quantity": 9},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Launch 10 concurrent worker tasks
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()  # Release all tasks simultaneously
        responses = await asyncio.gather(*tasks)

        # Analyze HTTP response codes
        status_codes = [r.status_code for r in responses]
        success_count = status_codes.count(200)
        conflict_count = status_codes.count(409)

        assert success_count == 1, f"Expected exactly 1 success, got {success_count} (statuses: {status_codes})"
        assert conflict_count == 9, f"Expected exactly 9 conflicts, got {conflict_count} (statuses: {status_codes})"

        # Assert final DB state
        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_state = res_check.json()
        assert inv_state["available_quantity"] == 0
        assert inv_state["reserved_quantity"] == 9
        assert inv_state["available_quantity"] >= 0

        # Assert historical movement log
        res_mov = await client.get(
            f"/v1/inventory/{inv_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
        )
        movements = res_mov.json()
        assert len(movements) == 1
        assert movements[0]["movement_type"] == "RESERVATION"
        assert movements[0]["quantity"] == -9


@pytest.mark.asyncio
async def test_multiple_valid_reservations_concurrency():
    """Verifies system allows multiple valid concurrent reservations when stock is sufficient.
    Initial stock: available=10. 10 concurrent requests for 1 unit each.
    Asserts: All 10 succeed (200 OK), final available=0, reserved=10.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Multi Concurrency",
        email="multi_conc@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SELLER_2", name="Conc Seller 2"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-SKU-10", name="Multi Item", seller_id=seller.id)
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

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/inventory/{inv_id}/reserve",
                json={"quantity": 1},
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 10

        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_state = res_check.json()
        assert inv_state["available_quantity"] == 0
        assert inv_state["reserved_quantity"] == 10


@pytest.mark.asyncio
async def test_boundary_concurrency_case():
    """Verifies boundary condition: initial available=9, 10 concurrent requests for 1 unit each.
    Asserts: 9 succeed, 1 fails with 409, final available=0, reserved=9.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Boundary Concurrency",
        email="bound_conc@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SELLER_3", name="Conc Seller 3"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-SKU-BOUND", name="Boundary Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_init = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 9},
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_id = res_init.json()["id"]

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/inventory/{inv_id}/reserve",
                json={"quantity": 1},
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 9
        assert status_codes.count(409) == 1

        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_state = res_check.json()
        assert inv_state["available_quantity"] == 0
        assert inv_state["reserved_quantity"] == 9


@pytest.mark.asyncio
async def test_all_fail_concurrency_case():
    """Verifies that when requested quantity exceeds available stock for all requests, all 10 fail with 409 and stock is unchanged.
    Initial stock: available=5. 10 concurrent requests for 6 units each.
    Asserts: 0 succeed, 10 fail (409 Conflict), final available=5, reserved=0.
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin All Fail Concurrency",
        email="fail_conc@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SELLER_4", name="Conc Seller 4"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-SKU-FAIL", name="All Fail Item", seller_id=seller.id)
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

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/inventory/{inv_id}/reserve",
                json={"quantity": 6},
                headers={"Authorization": f"Bearer {token}"},
            )

        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 0
        assert status_codes.count(409) == 10

        res_check = await client.get(
            f"/v1/inventory/{inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        inv_state = res_check.json()
        assert inv_state["available_quantity"] == 5
        assert inv_state["reserved_quantity"] == 0


@pytest.mark.asyncio
async def test_warehouse_isolation_concurrency():
    """Verifies that concurrent reservations on RENO stock leave COLUMBUS stock completely untouched."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Wh Iso Concurrency",
        email="iso_conc@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_SELLER_5", name="Conc Seller 5"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-SKU-ISO", name="Warehouse Iso Item", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create RENO inventory (9 available)
        res_reno = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "RENO", "initial_available": 9},
            headers={"Authorization": f"Bearer {token}"},
        )
        reno_inv_id = res_reno.json()["id"]

        # Create COLUMBUS inventory (9 available)
        res_col = await client.post(
            "/v1/inventory",
            json={"product_id": product.id, "warehouse_code": "COLUMBUS", "initial_available": 9},
            headers={"Authorization": f"Bearer {token}"},
        )
        col_inv_id = res_col.json()["id"]

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                f"/v1/inventory/{reno_inv_id}/reserve",
                json={"quantity": 9},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Launch 10 concurrent requests against RENO only
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()
        await asyncio.gather(*tasks)

        # Assert COLUMBUS inventory is completely untouched
        res_col_check = await client.get(
            f"/v1/inventory/{col_inv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        col_state = res_col_check.json()
        assert col_state["available_quantity"] == 9
        assert col_state["reserved_quantity"] == 0
