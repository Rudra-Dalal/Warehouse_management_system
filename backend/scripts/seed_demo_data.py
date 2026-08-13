import argparse
import asyncio
import os
import sys

# Ensure backend root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bson import ObjectId
from fastapi import HTTPException
from commons.logger import get_logger
from core.apis.schemas.requests.fulfillment_request import (
    FulfillmentCreateRequest,
    PackFulfillmentRequest,
    PickFulfillmentRequest,
    PickItemRequest,
    ShipFulfillmentRequest,
)
from core.apis.schemas.requests.inventory_request import InventoryCreateRequest
from core.apis.schemas.requests.order_request import OrderCreateRequest, OrderItemRequest
from core.apis.schemas.requests.product_request import ProductCreateRequest
from core.apis.schemas.requests.receiving_request import ReceivingCreateRequest, ReceivingItemRequest
from core.apis.schemas.requests.seller_request import SellerCreateRequest
from core.controllers.fulfillment_controller import FulfillmentController
from core.controllers.inventory_controller import InventoryController
from core.controllers.order_controller import OrderController
from core.controllers.product_controller import ProductController
from core.controllers.receiving_controller import ReceivingController
from core.controllers.seller_controller import SellerController
from core.cruds.user_crud import UserCRUD
from core.database.database import DatabaseManager, seed_fixed_warehouses
from core.database.seed_rbac import seed_rbac_data

logger = get_logger(__name__)


async def reset_demo_data() -> None:
    """Safely purges only records created by the demo seeding script (identified by DEMO_ prefixes).
    Leaves system roles, permissions, fixed warehouses, handbook RAG data, and real users untouched.
    """
    logger.info("Starting safe reset of demo WMS data...")
    db = DatabaseManager.get_db()

    # Find demo sellers
    demo_sellers = await db["sellers"].find({"code": {"$regex": "^DEMO_SELLER_"}}).to_list(100)
    demo_seller_ids = [str(s["_id"]) for s in demo_sellers]

    # Find demo products
    demo_products = await db["products"].find({"sku": {"$regex": "^DEMO_SKU_"}}).to_list(100)
    demo_product_ids = [str(p["_id"]) for p in demo_products]

    # Find demo orders
    demo_orders = await db["orders"].find({"order_number": {"$regex": "^DEMO_ORD_"}}).to_list(100)
    demo_order_ids = [str(o["_id"]) for o in demo_orders]

    # Find demo receiving shipments
    demo_receivings = await db["receiving_shipments"].find({"receiving_reference": {"$regex": "^DEMO_REC_"}}).to_list(100)
    demo_receiving_ids = [str(r["_id"]) for r in demo_receivings]

    # 1. Delete Demo Fulfillments
    del_ful = await db["fulfillments"].delete_many(
        {"$or": [{"order_number": {"$regex": "^DEMO_ORD_"}}, {"order_id": {"$in": demo_order_ids}}]}
    )
    logger.info(f"Deleted {del_ful.deleted_count} demo fulfillment tasks")

    # 2. Delete Demo Orders
    del_ord = await db["orders"].delete_many({"order_number": {"$regex": "^DEMO_ORD_"}})
    logger.info(f"Deleted {del_ord.deleted_count} demo orders")

    # 3. Delete Demo Receiving Shipments
    del_rec = await db["receiving_shipments"].delete_many({"receiving_reference": {"$regex": "^DEMO_REC_"}})
    logger.info(f"Deleted {del_rec.deleted_count} demo receiving shipments")

    # 4. Delete Demo Inventory Records
    del_inv = await db["inventory"].delete_many({"product_id": {"$in": demo_product_ids}})
    logger.info(f"Deleted {del_inv.deleted_count} demo inventory records")

    # 5. Delete Demo Inventory Movements
    del_mov = await db["inventory_movements"].delete_many(
        {"$or": [{"product_id": {"$in": demo_product_ids}}, {"note": {"$regex": r"\[DEMO\]"}}]}
    )
    logger.info(f"Deleted {del_mov.deleted_count} demo inventory movements")

    # 6. Delete Demo Products
    del_prod = await db["products"].delete_many({"sku": {"$regex": "^DEMO_SKU_"}})
    logger.info(f"Deleted {del_prod.deleted_count} demo products")

    # 7. Delete Demo Sellers
    del_sel = await db["sellers"].delete_many({"code": {"$regex": "^DEMO_SELLER_"}})
    logger.info(f"Deleted {del_sel.deleted_count} demo sellers")

    # 8. Delete Demo Audit Logs
    del_aud = await db["audit_logs"].delete_many(
        {
            "$or": [
                {"entity_id": {"$in": demo_seller_ids + demo_product_ids + demo_order_ids + demo_receiving_ids}},
                {"metadata.demo": True},
            ]
        }
    )
    logger.info(f"Deleted {del_aud.deleted_count} demo audit log entries")

    logger.info("Safe demo data reset completed successfully!")


async def seed_demo_data() -> None:
    """Idempotently seeds a rich, realistic, internally consistent demo dataset for the WMS."""
    logger.info("Executing seed_demo_data...")
    await DatabaseManager.connect_to_database()
    db = DatabaseManager.get_db()

    # Ensure RBAC and warehouses are initialized
    await seed_rbac_data()
    await seed_fixed_warehouses()

    user_crud = UserCRUD()
    admin_user = await user_crud.get_by_email("admin@whitfield.com")
    if not admin_user:
        raise RuntimeError("Seed admin user admin@whitfield.com not found.")

    seller_controller = SellerController()
    product_controller = ProductController()
    inventory_controller = InventoryController()
    receiving_controller = ReceivingController()
    order_controller = OrderController()
    fulfillment_controller = FulfillmentController()

    # -------------------------------------------------------------
    # 1. SELLERS (5 Realistic Demo Sellers)
    # -------------------------------------------------------------
    sellers_data = [
        {"code": "DEMO_SELLER_001", "name": "Apex Electronics Ltd", "email": "contact@apexelectronics.com", "phone": "+1-800-555-0199"},
        {"code": "DEMO_SELLER_002", "name": "Aurora Home & Living", "email": "support@aurorahome.com", "phone": "+1-800-555-0288"},
        {"code": "DEMO_SELLER_003", "name": "Kinetic Fitness Gear", "email": "sales@kineticfitness.com", "phone": "+1-800-555-0377"},
        {"code": "DEMO_SELLER_004", "name": "Paper & Quill Office Supplies", "email": "orders@paperquill.com", "phone": "+1-800-555-0466"},
        {"code": "DEMO_SELLER_005", "name": "Vanguard Consumer Goods", "email": "hello@vanguardgoods.com", "phone": "+1-800-555-0555"},
    ]

    seller_map = {}
    for s_info in sellers_data:
        existing = await seller_controller.seller_crud.get_by_code(s_info["code"])
        if not existing:
            created = await seller_controller.create_seller(
                SellerCreateRequest(**s_info), current_user=admin_user
            )
            seller_map[s_info["code"]] = created.id
            logger.info(f"[SEED] Created seller {s_info['name']} ({s_info['code']})")
        else:
            seller_map[s_info["code"]] = existing.id
            logger.info(f"[EXISTS] Seller {s_info['code']} already exists")

    # -------------------------------------------------------------
    # 2. PRODUCTS (18 Realistic Products with Leading-Zero UPCs)
    # -------------------------------------------------------------
    products_data = [
        # Seller 1: Electronics
        {
            "seller_code": "DEMO_SELLER_001",
            "sku": "DEMO_SKU_001",
            "name": "Wireless Ergonomic Keyboard",
            "description": "Dual-mode 2.4G/Bluetooth quiet tactile keyboard",
            "upc": "000123456789",
        },
        {
            "seller_code": "DEMO_SELLER_001",
            "sku": "DEMO_SKU_002",
            "name": "USB-C 7-in-1 Multiport Hub",
            "description": "4K HDMI, 100W PD pass-through, 3x USB 3.0 SD reader",
            "upc": "001234567890",
        },
        {
            "seller_code": "DEMO_SELLER_001",
            "sku": "DEMO_SKU_003",
            "name": "Noise-Canceling Wireless Earbuds",
            "description": "Active ANC bluetooth 5.3 earbuds with wireless case",
            "upc": "000987654321",
        },
        {
            "seller_code": "DEMO_SELLER_001",
            "sku": "DEMO_SKU_004",
            "name": "Portable Bluetooth Speaker",
            "description": "IPX7 waterproof 20W stereo bass outdoor speaker",
            "upc": "005566778899",
        },
        # Seller 2: Home & Living
        {
            "seller_code": "DEMO_SELLER_002",
            "sku": "DEMO_SKU_005",
            "name": "LED Smart Desk Lamp",
            "description": "Dimmable eye-caring desk lamp with wireless charger",
            "upc": "005544332211",
        },
        {
            "seller_code": "DEMO_SELLER_002",
            "sku": "DEMO_SKU_006",
            "name": "Stainless Steel Thermal Bottle",
            "description": "Double-wall vacuum insulated 32oz water bottle",
            "upc": "007571301499",
        },
        {
            "seller_code": "DEMO_SELLER_002",
            "sku": "DEMO_SKU_007",
            "name": "Modular Desktop Storage Bin",
            "description": "Stackable translucent organizer bin 3-pack",
            "upc": "001122334455",
        },
        {
            "seller_code": "DEMO_SELLER_002",
            "sku": "DEMO_SKU_008",
            "name": "Ceramic Coffee Travel Mug",
            "description": "16oz splash-proof insulated travel coffee mug",
            "upc": "006677889900",
        },
        # Seller 3: Fitness
        {
            "seller_code": "DEMO_SELLER_003",
            "sku": "DEMO_SKU_009",
            "name": "Pro Resistance Bands Set",
            "description": "5-level heavy duty latex workout resistance bands",
            "upc": "002233445566",
        },
        {
            "seller_code": "DEMO_SELLER_003",
            "sku": "DEMO_SKU_010",
            "name": "Non-Slip Alignment Yoga Mat",
            "description": "6mm eco-friendly TPE yoga mat with carrying strap",
            "upc": "003344556677",
        },
        {
            "seller_code": "DEMO_SELLER_003",
            "sku": "DEMO_SKU_011",
            "name": "High-Speed Jump Rope",
            "description": "Tangle-free ball bearing speed rope for cardio fitness",
            "upc": "004455667788",
        },
        # Seller 4: Office Supplies
        {
            "seller_code": "DEMO_SELLER_004",
            "sku": "DEMO_SKU_012",
            "name": "Executive Hardcover Journal",
            "description": "A5 thick 120gsm grid paper notebook with ribbon marker",
            "upc": "008899001122",
        },
        {
            "seller_code": "DEMO_SELLER_004",
            "sku": "DEMO_SKU_013",
            "name": "Mechanical Pencil Set 0.5mm",
            "description": "Metal drafting pencils 3-pack with HB lead refills",
            "upc": "009900112233",
        },
        {
            "seller_code": "DEMO_SELLER_004",
            "sku": "DEMO_SKU_014",
            "name": "Aluminum Monitor Riser",
            "description": "Ergonomic laptop/monitor stand with keyboard storage",
            "upc": "001100223344",
        },
        # Seller 5: Consumer Goods
        {
            "seller_code": "DEMO_SELLER_005",
            "sku": "DEMO_SKU_015",
            "name": "Microfiber Cleaning Cloth 10-Pack",
            "description": "Ultra-absorbent lint-free microfiber towels",
            "upc": "002211334455",
        },
        {
            "seller_code": "DEMO_SELLER_005",
            "sku": "DEMO_SKU_016",
            "name": "Compact First Aid Kit",
            "description": "100-piece emergency medical kit for travel & office",
            "upc": "003322445566",
        },
        {
            "seller_code": "DEMO_SELLER_005",
            "sku": "DEMO_SKU_017",
            "name": "Eco-Friendly Canvas Tote Bag",
            "description": "Heavy duty cotton canvas grocery tote bag",
            "upc": "004433556677",
        },
        {
            "seller_code": "DEMO_SELLER_005",
            "sku": "DEMO_SKU_018",
            "name": "Reusable Cable Straps 20-Pack",
            "description": "Hook and loop cord management ties",
            "upc": "005544667788",
        },
    ]

    product_map = {}
    for p_info in products_data:
        existing_sku = await product_controller.product_crud.get_by_sku(p_info["sku"])
        if existing_sku:
            product_map[p_info["sku"]] = existing_sku.id
            logger.info(f"[EXISTS] Product {p_info['sku']} already exists")
            continue

        seller_id = seller_map[p_info["seller_code"]]
        try:
            created = await product_controller.create_product(
                ProductCreateRequest(
                    sku=p_info["sku"],
                    name=p_info["name"],
                    description=p_info["description"],
                    upc=p_info["upc"],
                    seller_id=seller_id,
                ),
                current_user=admin_user,
            )
            product_map[p_info["sku"]] = created.id
            logger.info(f"[SEED] Created product {p_info['name']} ({p_info['sku']}) with UPC '{p_info['upc']}'")
        except HTTPException as err:
            if err.status_code == 409 and "UPC" in str(err.detail):
                # UPC conflict -> lookup existing product by UPC
                existing_upc = await product_controller.product_crud.get_by_upc(p_info["upc"])
                if existing_upc:
                    product_map[p_info["sku"]] = existing_upc.id
                    logger.info(f"[EXISTS] Product with UPC '{p_info['upc']}' already exists")
            else:
                raise err

    # -------------------------------------------------------------
    # 3. INVENTORY (Realistic Varied Distribution across RENO & COLUMBUS)
    # -------------------------------------------------------------
    inventory_plan = [
        # (SKU, RENO_qty, COLUMBUS_qty)
        ("DEMO_SKU_001", 185, 92),   # High
        ("DEMO_SKU_002", 140, 75),   # High
        ("DEMO_SKU_003", 65, 40),    # Normal
        ("DEMO_SKU_004", 12, 18),    # Low stock
        ("DEMO_SKU_005", 85, 110),   # Normal/High
        ("DEMO_SKU_006", 210, 165),  # High
        ("DEMO_SKU_007", 3, 7),      # Critical / Low
        ("DEMO_SKU_008", 48, 55),    # Normal
        ("DEMO_SKU_009", 175, 80),   # High
        ("DEMO_SKU_010", 15, 22),    # Low
        ("DEMO_SKU_011", 2, 4),      # Critical
        ("DEMO_SKU_012", 95, 120),   # Normal/High
        ("DEMO_SKU_013", 160, 190),  # High
        ("DEMO_SKU_014", 8, 14),     # Low
        ("DEMO_SKU_015", 250, 210),  # High
        ("DEMO_SKU_016", 11, 16),    # Low
        ("DEMO_SKU_017", 78, 62),    # Normal
        ("DEMO_SKU_018", 130, 115),  # High
    ]

    for sku, reno_qty, columbus_qty in inventory_plan:
        if sku not in product_map:
            continue
        prod_id = product_map[sku]

        # Reno
        wh_reno = await db["warehouses"].find_one({"code": "RENO"})
        if wh_reno:
            existing_reno = await inventory_controller.inventory_crud.get_by_product_and_warehouse(
                product_id=prod_id,
                warehouse_id=str(wh_reno["_id"]),
            )
            if not existing_reno:
                await inventory_controller.create_inventory(
                    InventoryCreateRequest(
                        product_id=prod_id,
                        warehouse_code="RENO",
                        initial_available=reno_qty,
                    ),
                    current_user=admin_user,
                )
                logger.info(f"[SEED] Created RENO inventory for {sku}: {reno_qty} units")

        # Columbus
        wh_col = await db["warehouses"].find_one({"code": "COLUMBUS"})
        if wh_col:
            existing_col = await inventory_controller.inventory_crud.get_by_product_and_warehouse(
                product_id=prod_id,
                warehouse_id=str(wh_col["_id"]),
            )
            if not existing_col:
                await inventory_controller.create_inventory(
                    InventoryCreateRequest(
                        product_id=prod_id,
                        warehouse_code="COLUMBUS",
                        initial_available=columbus_qty,
                    ),
                    current_user=admin_user,
                )
                logger.info(f"[SEED] Created COLUMBUS inventory for {sku}: {columbus_qty} units")

    # -------------------------------------------------------------
    # 4. INBOUND RECEIVING SHIPMENTS (6 Shipments)
    # -------------------------------------------------------------
    receiving_plan = [
        {"ref": "DEMO_REC_001", "wh": "RENO", "seller": "DEMO_SELLER_001", "items": [("DEMO_SKU_001", 50), ("DEMO_SKU_002", 30)]},
        {"ref": "DEMO_REC_002", "wh": "COLUMBUS", "seller": "DEMO_SELLER_002", "items": [("DEMO_SKU_005", 40), ("DEMO_SKU_006", 60)]},
        {"ref": "DEMO_REC_003", "wh": "RENO", "seller": "DEMO_SELLER_003", "items": [("DEMO_SKU_009", 50), ("DEMO_SKU_010", 20)]},
        {"ref": "DEMO_REC_004", "wh": "COLUMBUS", "seller": "DEMO_SELLER_004", "items": [("DEMO_SKU_012", 30), ("DEMO_SKU_013", 50)]},
        {"ref": "DEMO_REC_005", "wh": "RENO", "seller": "DEMO_SELLER_005", "items": [("DEMO_SKU_015", 100), ("DEMO_SKU_018", 40)]},
        {"ref": "DEMO_REC_006", "wh": "COLUMBUS", "seller": "DEMO_SELLER_001", "items": [("DEMO_SKU_003", 25), ("DEMO_SKU_004", 15)]},
    ]

    for rec_info in receiving_plan:
        existing_rec = await db["receiving_shipments"].find_one({"receiving_reference": rec_info["ref"]})
        if not existing_rec:
            items_req = [
                ReceivingItemRequest(product_id=product_map[sku], quantity=qty)
                for sku, qty in rec_info["items"]
                if sku in product_map
            ]
            if items_req and rec_info["seller"] in seller_map:
                seller_id = seller_map[rec_info["seller"]]
                await receiving_controller.receive_shipment(
                    ReceivingCreateRequest(
                        receiving_reference=rec_info["ref"],
                        warehouse_code=rec_info["wh"],
                        seller_id=seller_id,
                        items=items_req,
                    ),
                    current_user=admin_user,
                )
                logger.info(f"[SEED] Created receiving shipment {rec_info['ref']} at {rec_info['wh']}")
        else:
            logger.info(f"[EXISTS] Receiving shipment {rec_info['ref']} already exists")

    # -------------------------------------------------------------
    # 5. ORDERS & FULFILLMENT TASKS (12 Orders Across State Machine)
    # -------------------------------------------------------------
    orders_plan = [
        # (Order Number, Warehouse, Seller Code, Items [(SKU, Qty)], Target Status)
        ("DEMO_ORD_001", "RENO", "DEMO_SELLER_001", [("DEMO_SKU_001", 2)], "READY_TO_PICK"),
        ("DEMO_ORD_002", "RENO", "DEMO_SELLER_002", [("DEMO_SKU_005", 1)], "READY_TO_PICK"),
        ("DEMO_ORD_003", "COLUMBUS", "DEMO_SELLER_003", [("DEMO_SKU_009", 3)], "READY_TO_PICK"),
        ("DEMO_ORD_004", "RENO", "DEMO_SELLER_004", [("DEMO_SKU_012", 2)], "PICKED"),
        ("DEMO_ORD_005", "COLUMBUS", "DEMO_SELLER_005", [("DEMO_SKU_015", 5)], "PICKED"),
        ("DEMO_ORD_006", "RENO", "DEMO_SELLER_001", [("DEMO_SKU_002", 1)], "PICKED"),
        ("DEMO_ORD_007", "COLUMBUS", "DEMO_SELLER_002", [("DEMO_SKU_006", 2)], "PACKED"),
        ("DEMO_ORD_008", "RENO", "DEMO_SELLER_003", [("DEMO_SKU_009", 1)], "PACKED"),
        ("DEMO_ORD_009", "COLUMBUS", "DEMO_SELLER_004", [("DEMO_SKU_013", 4)], "PACKED"),
        ("DEMO_ORD_010", "RENO", "DEMO_SELLER_005", [("DEMO_SKU_018", 2)], "SHIPPED"),
        ("DEMO_ORD_011", "COLUMBUS", "DEMO_SELLER_001", [("DEMO_SKU_001", 1)], "SHIPPED"),
        ("DEMO_ORD_012", "RENO", "DEMO_SELLER_002", [("DEMO_SKU_008", 3)], "SHIPPED"),
    ]

    for ord_num, wh_code, sel_code, line_items, target_status in orders_plan:
        existing_order = await db["orders"].find_one({"order_number": ord_num})
        if not existing_order:
            order_items = [
                OrderItemRequest(product_id=product_map[sku], quantity=qty)
                for sku, qty in line_items
                if sku in product_map
            ]
            if order_items and sel_code in seller_map:
                created_order = await order_controller.create_and_confirm_order(
                    OrderCreateRequest(
                        order_number=ord_num,
                        seller_id=seller_map[sel_code],
                        warehouse_code=wh_code,
                        items=order_items,
                    ),
                    current_user=admin_user,
                )
                logger.info(f"[SEED] Created order {ord_num} ({target_status})")

                # Create fulfillment task
                ful_res = await fulfillment_controller.create_fulfillment(
                    FulfillmentCreateRequest(order_id=created_order.id),
                    current_user=admin_user,
                )
                ful_id = ful_res.id

                # Progress fulfillment through state machine based on target_status
                if target_status in ("PICKED", "PACKED", "SHIPPED"):
                    pick_items = [
                        PickItemRequest(product_id=product_map[sku], quantity=qty)
                        for sku, qty in line_items
                        if sku in product_map
                    ]
                    await fulfillment_controller.pick_fulfillment(
                        ful_id,
                        PickFulfillmentRequest(items=pick_items),
                        current_user=admin_user,
                    )
                    logger.info(f"[SEED] Fulfillment {ord_num} -> PICKED")

                if target_status in ("PACKED", "SHIPPED"):
                    await fulfillment_controller.pack_fulfillment(
                        ful_id,
                        PackFulfillmentRequest(note="Packed with standard padding"),
                        current_user=admin_user,
                    )
                    logger.info(f"[SEED] Fulfillment {ord_num} -> PACKED")

                if target_status == "SHIPPED":
                    tracking_idx = int(ord_num.split("_")[-1])
                    await fulfillment_controller.ship_fulfillment(
                        ful_id,
                        ShipFulfillmentRequest(tracking_number=f"1Z99999999999999{tracking_idx:02d}"),
                        current_user=admin_user,
                    )
                    logger.info(f"[SEED] Fulfillment {ord_num} -> SHIPPED")
        else:
            logger.info(f"[EXISTS] Order {ord_num} already exists")

    logger.info("WMS Demo Data Seeding completed successfully!")


async def main():
    parser = argparse.ArgumentParser(description="Seed realistic demo data into Whitfield WMS")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Safely remove demo data matching DEMO_ prefixes without touching system roles or RAG data",
    )
    args = parser.parse_args()

    await DatabaseManager.connect_to_database()

    if args.reset:
        await reset_demo_data()
    else:
        await seed_demo_data()

    await DatabaseManager.close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())
