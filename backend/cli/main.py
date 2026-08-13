import argparse
import sys
from typing import Any

from cli.client.auth_client import get_token
from cli.client.api_client import make_request, APIError
from cli.ui.output import print_success
from cli.ui.errors import print_error_and_exit

# Command Handlers
from cli.commands.auth import handle_login, handle_logout, handle_whoami
from cli.commands.inventory import (
    handle_inventory_list,
    handle_inventory_get,
    handle_inventory_adjust,
    handle_inventory_reserve,
    handle_inventory_movements,
)
from cli.commands.products import (
    handle_products_list,
    handle_products_get,
    handle_products_sku,
    handle_products_upc,
    handle_products_scan,
)
from cli.commands.receiving import (
    handle_receiving_list,
    handle_receiving_get,
    handle_receiving_create,
)
from cli.commands.orders import (
    handle_orders_list,
    handle_orders_get,
    handle_orders_create,
)
from cli.commands.fulfillment import (
    handle_fulfillment_list,
    handle_fulfillment_get,
    handle_fulfillment_create,
    handle_fulfillment_pick,
    handle_fulfillment_pack,
    handle_fulfillment_ship,
)
from cli.commands.audit import (
    handle_audit_list,
    handle_audit_get,
    handle_audit_entity,
    handle_audit_user,
)

def handle_health(args) -> None:
    """Checks the health of the FastAPI backend over HTTP."""
    try:
        res = make_request("GET", "/health")
        print_success("Service is healthy.", res)
    except APIError as e:
        print_error_and_exit(e)

def main() -> None:
    """Entry point for the Whitfield Fulfillment WMS CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="Whitfield Fulfillment WMS Command Line Interface"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Root commands
    subparsers.add_parser("health", help="Check WMS API service health")
    subparsers.add_parser("login", help="Authenticate and retrieve JWT session token")
    subparsers.add_parser("logout", help="Clear local session JWT token")
    subparsers.add_parser("whoami", help="Display current authenticated user details")

    # --- Inventory Subcommands ---
    inv_parser = subparsers.add_parser("inventory", help="Inventory stock operations")
    inv_sub = inv_parser.add_subparsers(dest="subcommand")

    inv_list = inv_sub.add_parser("list", help="List stock levels")
    inv_list.add_argument("--warehouse-code", help="Filter by warehouse code (RENO/COLUMBUS)")
    inv_list.add_argument("--sku", help="Filter by product SKU")
    inv_list.add_argument("--product-id", help="Filter by product ID")

    inv_get = inv_sub.add_parser("get", help="Get inventory record details")
    inv_get.add_argument("inventory_id", help="Inventory ObjectId string")

    inv_adjust = inv_sub.add_parser("adjust", help="Adjust available stock level")
    inv_adjust.add_argument("inventory_id", help="Inventory ObjectId string")
    inv_adjust.add_argument("--quantity", type=int, required=True, help="Signed quantity adjustment delta")
    inv_adjust.add_argument("--note", help="Reason for adjustment")

    inv_reserve = inv_sub.add_parser("reserve", help="Reserve available stock")
    inv_reserve.add_argument("inventory_id", help="Inventory ObjectId string")
    inv_reserve.add_argument("--quantity", type=int, required=True, help="Positive integer quantity to reserve")

    inv_movements = inv_sub.add_parser("movements", help="List stock movement logs")
    inv_movements.add_argument("inventory_id", help="Inventory ObjectId string")

    # --- Products Subcommands ---
    prod_parser = subparsers.add_parser("products", help="Product catalog operations")
    prod_sub = prod_parser.add_subparsers(dest="subcommand")

    prod_list = prod_sub.add_parser("list", help="List catalog products")
    prod_list.add_argument("--seller-id", help="Filter by seller ID")

    prod_get = prod_sub.add_parser("get", help="Get product details")
    prod_get.add_argument("product_id", help="Product ObjectId string")

    prod_sku = prod_sub.add_parser("sku", help="Lookup product by SKU")
    prod_sku.add_argument("sku", help="Product SKU code")

    prod_upc = prod_sub.add_parser("upc", help="Lookup product by UPC barcode")
    prod_upc.add_argument("upc", help="Product UPC barcode string")

    prod_scan = prod_sub.add_parser("scan", help="Scan/lookup product barcode string")
    prod_scan.add_argument("barcode", nargs="?", help="Product barcode string input")

    # --- Receiving Subcommands ---
    rec_parser = subparsers.add_parser("receiving", help="Inbound receiving shipments")
    rec_sub = rec_parser.add_subparsers(dest="subcommand")

    rec_list = rec_sub.add_parser("list", help="List receiving shipments")
    rec_list.add_argument("--warehouse-code", help="Filter by warehouse code (RENO/COLUMBUS)")
    rec_list.add_argument("--seller-id", help="Filter by seller ID")

    rec_get = rec_sub.add_parser("get", help="Get receiving shipment details")
    rec_get.add_argument("receiving_id", help="Receiving ObjectId string")

    rec_create = rec_sub.add_parser("create", help="Create and process receiving shipment")
    rec_create.add_argument("--reference", required=True, help="Unique shipment reference")
    rec_create.add_argument("--warehouse-code", required=True, help="Target warehouse code (RENO/COLUMBUS)")
    rec_create.add_argument("--seller-id", required=True, help="Seller ObjectId string")
    rec_create.add_argument("--items", required=True, help="Comma-separated items list (product_id:quantity)")

    # --- Orders Subcommands ---
    order_parser = subparsers.add_parser("orders", help="Customer order workflows")
    order_sub = order_parser.add_subparsers(dest="subcommand")

    order_list = order_sub.add_parser("list", help="List customer orders")
    order_list.add_argument("--warehouse-code", help="Filter by warehouse code (RENO/COLUMBUS)")
    order_list.add_argument("--seller-id", help="Filter by seller ID")
    order_list.add_argument("--status", help="Filter by status (CREATED/CONFIRMED)")

    order_get = order_sub.add_parser("get", help="Get order details")
    order_get.add_argument("order_id", help="Order ObjectId string")

    order_create = order_sub.add_parser("create", help="Create and confirm customer order")
    order_create.add_argument("--order-number", required=True, help="Unique order number")
    order_create.add_argument("--warehouse-code", required=True, help="Target warehouse code (RENO/COLUMBUS)")
    order_create.add_argument("--seller-id", required=True, help="Seller ObjectId string")
    order_create.add_argument("--items", required=True, help="Comma-separated order items (product_id:quantity)")

    # --- Fulfillment Subcommands ---
    ful_parser = subparsers.add_parser("fulfillment", help="Fulfillment execution workflows")
    ful_sub = ful_parser.add_subparsers(dest="subcommand")

    ful_list = ful_sub.add_parser("list", help="List fulfillment tasks")
    ful_list.add_argument("--warehouse-code", help="Filter by warehouse code (RENO/COLUMBUS)")
    ful_list.add_argument("--status", help="Filter by status (READY_TO_PICK/PICKED/PACKED/SHIPPED)")

    ful_get = ful_sub.add_parser("get", help="Get fulfillment task details")
    ful_get.add_argument("fulfillment_id", help="Fulfillment ObjectId string")

    ful_create = ful_sub.add_parser("create", help="Initiate fulfillment task for order")
    ful_create.add_argument("--order-id", required=True, help="Order ObjectId string")

    ful_pick = ful_sub.add_parser("pick", help="Pick items for fulfillment task")
    ful_pick.add_argument("fulfillment_id", help="Fulfillment ObjectId string")
    ful_pick.add_argument("--items", required=True, help="Comma-separated items (product_id:quantity)")

    ful_pack = ful_sub.add_parser("pack", help="Pack items for fulfillment task")
    ful_pack.add_argument("fulfillment_id", help="Fulfillment ObjectId string")
    ful_pack.add_argument("--note", help="Optional packing notes")

    ful_ship = ful_sub.add_parser("ship", help="Ship order and assign tracking")
    ful_ship.add_argument("fulfillment_id", help="Fulfillment ObjectId string")
    ful_ship.add_argument("--tracking", help="Optional tracking reference string")

    # --- Audit Subcommands ---
    audit_parser = subparsers.add_parser("audit", help="Read system audit log records")
    audit_sub = audit_parser.add_subparsers(dest="subcommand")

    audit_list = audit_sub.add_parser("list", help="List audit trail records")
    audit_list.add_argument("--action", help="Filter by action name")
    audit_list.add_argument("--entity-type", help="Filter by entity type")
    audit_list.add_argument("--entity-id", help="Filter by entity ID")
    audit_list.add_argument("--user-id", help="Filter by user ID")
    audit_list.add_argument("--warehouse-code", help="Filter by warehouse code")
    audit_list.add_argument("--reference-type", help="Filter by reference context category")
    audit_list.add_argument("--reference-id", help="Filter by reference entity ID")
    audit_list.add_argument("--success", type=lambda x: (str(x).lower() == 'true'), help="Filter success boolean (true/false)")
    audit_list.add_argument("--limit", type=int, default=50, help="Pagination limit")
    audit_list.add_argument("--offset", type=int, default=0, help="Pagination offset")

    audit_get = audit_sub.add_parser("get", help="Get specific audit record details")
    audit_get.add_argument("audit_id", help="Audit ObjectId string")

    audit_ent = audit_sub.add_parser("entity", help="Get history for specific entity")
    audit_ent.add_argument("entity_type", help="Entity type name")
    audit_ent.add_argument("entity_id", help="Entity ObjectId string")
    audit_ent.add_argument("--limit", type=int, default=50, help="Pagination limit")
    audit_ent.add_argument("--offset", type=int, default=0, help="Pagination offset")

    audit_usr = audit_sub.add_parser("user", help="Get history of actions by specific user")
    audit_usr.add_argument("user_id", help="User ObjectId string")
    audit_usr.add_argument("--limit", type=int, default=50, help="Pagination limit")
    audit_usr.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Check for authentication on commands that require it
    authenticated_commands = {"inventory", "products", "receiving", "orders", "fulfillment", "audit"}
    if args.command in authenticated_commands:
        if not get_token():
            print(
                "Authentication required. Please login first:\n  python -m cli login",
                file=sys.stderr
            )
            sys.exit(1)

    # Route command to appropriate handler
    if args.command == "health":
        handle_health(args)
    elif args.command == "login":
        handle_login(args)
    elif args.command == "logout":
        handle_logout(args)
    elif args.command == "whoami":
        handle_whoami(args)
    elif args.command == "inventory":
        if not args.subcommand:
            inv_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_inventory_list(args)
        elif args.subcommand == "get":
            handle_inventory_get(args)
        elif args.subcommand == "adjust":
            handle_inventory_adjust(args)
        elif args.subcommand == "reserve":
            handle_inventory_reserve(args)
        elif args.subcommand == "movements":
            handle_inventory_movements(args)
    elif args.command == "products":
        if not args.subcommand:
            prod_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_products_list(args)
        elif args.subcommand == "get":
            handle_products_get(args)
        elif args.subcommand == "sku":
            handle_products_sku(args)
        elif args.subcommand == "upc":
            handle_products_upc(args)
        elif args.subcommand == "scan":
            handle_products_scan(args)
    elif args.command == "receiving":
        if not args.subcommand:
            rec_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_receiving_list(args)
        elif args.subcommand == "get":
            handle_receiving_get(args)
        elif args.subcommand == "create":
            handle_receiving_create(args)
    elif args.command == "orders":
        if not args.subcommand:
            order_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_orders_list(args)
        elif args.subcommand == "get":
            handle_orders_get(args)
        elif args.subcommand == "create":
            handle_orders_create(args)
    elif args.command == "fulfillment":
        if not args.subcommand:
            ful_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_fulfillment_list(args)
        elif args.subcommand == "get":
            handle_fulfillment_get(args)
        elif args.subcommand == "create":
            handle_fulfillment_create(args)
        elif args.subcommand == "pick":
            handle_fulfillment_pick(args)
        elif args.subcommand == "pack":
            handle_fulfillment_pack(args)
        elif args.subcommand == "ship":
            handle_fulfillment_ship(args)
    elif args.command == "audit":
        if not args.subcommand:
            audit_parser.print_help()
            sys.exit(0)
        if args.subcommand == "list":
            handle_audit_list(args)
        elif args.subcommand == "get":
            handle_audit_get(args)
        elif args.subcommand == "entity":
            handle_audit_entity(args)
        elif args.subcommand == "user":
            handle_audit_user(args)
