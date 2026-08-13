import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.inventory_movement_crud import InventoryMovementCRUD
from core.cruds.product_crud import ProductCRUD
from core.cruds.receiving_crud import ReceivingCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.database.database import DatabaseManager
from core.models.product_model import ProductModel
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_primary_concurrent_duplicate_receiving():
    """THE PRIMARY PHASE 5 CONCURRENCY & IDEMPOTENCY TEST:
    Initial stock: available=0.
    10 concurrent identical receiving requests for WH-REC-CONC-001 (100 units).
    Asserts: All 10 requests return 200 OK with the SAME shipment ID.
    Final DB state: available_quantity=100 (NOT 1000), exactly 1 receiving shipment,
    and exactly 1 RECEIVING movement (+100).
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Conc Rec Test",
        email="conc_rec@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_REC_SELLER_1", name="Conc Rec Seller 1"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-REC-SKU-100", name="Conc Rec Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "receiving_reference": "WH-REC-CONC-001",
            "warehouse_code": "RENO",
            "seller_id": seller.id,
            "items": [{"product_id": product.id, "quantity": 100}],
        }

        start_event = asyncio.Event()

        async def worker():
            await start_event.wait()
            return await client.post(
                "/v1/receiving",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )

        # Launch 10 concurrent worker tasks
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_event.set()  # Release all tasks simultaneously
        responses = await asyncio.gather(*tasks)

        # Analyze HTTP status codes and returned shipment IDs
        status_codes = [r.status_code for r in responses]
        assert status_codes == [200] * 10, f"All requests must return 200 OK, got {status_codes}"

        shipment_ids = {r.json()["id"] for r in responses}
        assert len(shipment_ids) == 1, f"Expected exactly 1 shipment ID across all responses, got {shipment_ids}"

        # Assert DB receiving shipments count
        rec_crud = ReceivingCRUD()
        shipment = await rec_crud.get_by_reference("WH-REC-CONC-001")
        assert shipment is not None
        assert shipment.status == "RECEIVED"

        # Assert DB Inventory stock: available_quantity=100 (NOT 1000)
        inv_crud = InventoryCRUD()
        db = DatabaseManager.get_db()
        reno_doc = await db["warehouses"].find_one({"code": "RENO"})
        reno_id = str(reno_doc["_id"])
        inv = await inv_crud.get_by_product_and_warehouse(product.id, reno_id)
        assert inv is not None
        assert inv.available_quantity == 100, f"Expected available_quantity=100, got {inv.available_quantity}"

        # Assert DB Historical Movements: exactly 1 RECEIVING movement (+100)
        mov_crud = InventoryMovementCRUD()
        movements = await mov_crud.list_movements_by_context(product.id, reno_id)
        assert len(movements) == 1
        assert movements[0].movement_type == "RECEIVING"
        assert movements[0].quantity == 100


@pytest.mark.asyncio
async def test_different_receiving_references_concurrency():
    """Verifies that different receiving references (WH-REC-A and WH-REC-B) process concurrently and independently.
    Initial stock: 0. Request A (+100) and Request B (+200) run concurrently.
    Final DB state: available_quantity=300, 2 shipments, 2 RECEIVING movements (+100 and +200).
    """
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Diff Conc Test",
        email="diff_conc_rec@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(SellerModel(code="CONC_REC_SELLER_2", name="Conc Rec Seller 2"))

    product_crud = ProductCRUD()
    product = await product_crud.create_product(
        ProductModel(sku="CONC-REC-SKU-DIFF", name="Diff Product", seller_id=seller.id)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start_event = asyncio.Event()

        async def worker(ref: str, qty: int):
            await start_event.wait()
            return await client.post(
                "/v1/receiving",
                json={
                    "receiving_reference": ref,
                    "warehouse_code": "RENO",
                    "seller_id": seller.id,
                    "items": [{"product_id": product.id, "quantity": qty}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        task_a = asyncio.create_task(worker("WH-REC-DIFF-A", 100))
        task_b = asyncio.create_task(worker("WH-REC-DIFF-B", 200))

        start_event.set()
        res_a, res_b = await asyncio.gather(task_a, task_b)

        assert res_a.status_code == 200
        assert res_b.status_code == 200

        # Verify DB inventory available_quantity = 300
        db = DatabaseManager.get_db()
        reno_doc = await db["warehouses"].find_one({"code": "RENO"})
        reno_id = str(reno_doc["_id"])

        inv_crud = InventoryCRUD()
        inv = await inv_crud.get_by_product_and_warehouse(product.id, reno_id)
        assert inv is not None
        assert inv.available_quantity == 300

        # Verify 2 RECEIVING movement logs
        mov_crud = InventoryMovementCRUD()
        movements = await mov_crud.list_movements_by_context(product.id, reno_id)
        assert len(movements) == 2
        quantities = {m.quantity for m in movements}
        assert quantities == {100, 200}
