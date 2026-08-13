from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object, print_success
from cli.ui.errors import print_error_and_exit

def handle_inventory_list(args) -> None:
    """Lists warehouse stock levels with optional warehouse, SKU, or product ID filters."""
    try:
        query_params = {}
        if args.warehouse_code:
            query_params["warehouse_code"] = args.warehouse_code
        if args.sku:
            query_params["sku"] = args.sku
        if args.product_id:
            query_params["product_id"] = args.product_id

        inventory_items = make_request("GET", "/v1/inventory", query_params=query_params)
        headers = ["ID", "Product ID", "SKU", "Warehouse Code", "Available", "Reserved", "Damaged"]
        rows = [
            [
                item.get("id"),
                item.get("product_id"),
                item.get("sku"),
                item.get("warehouse_code"),
                item.get("available_quantity"),
                item.get("reserved_quantity"),
                item.get("damaged_quantity"),
            ]
            for item in inventory_items
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_inventory_get(args) -> None:
    """Retrieves specific inventory details by string ObjectId."""
    try:
        item = make_request("GET", f"/v1/inventory/{args.inventory_id}")
        print_object(item)
    except APIError as e:
        print_error_and_exit(e)

def handle_inventory_adjust(args) -> None:
    """Adjusts available stock levels using a signed quantity delta and logs an InventoryMovement."""
    try:
        body = {
            "quantity_delta": args.quantity,
            "note": args.note
        }
        res = make_request("PATCH", f"/v1/inventory/{args.inventory_id}/adjust", body=body)
        print_success("Inventory adjusted successfully.", res)
    except APIError as e:
        print_error_and_exit(e)

def handle_inventory_reserve(args) -> None:
    """Atomically reserves stock for orders using an atomic MongoDB conditional update."""
    try:
        body = {
            "quantity": args.quantity
        }
        res = make_request("POST", f"/v1/inventory/{args.inventory_id}/reserve", body=body)
        print_success("Inventory reserved successfully.", res)
    except APIError as e:
        print_error_and_exit(e)

def handle_inventory_movements(args) -> None:
    """Retrieves historical InventoryMovement change logs for an inventory context."""
    try:
        movements = make_request("GET", f"/v1/inventory/{args.inventory_id}/movements")
        headers = ["ID", "Movement Type", "Quantity", "Reference Type", "User ID", "Created At"]
        rows = [
            [
                mov.get("id"),
                mov.get("movement_type"),
                mov.get("quantity"),
                mov.get("reference_type"),
                mov.get("user_id"),
                mov.get("created_at"),
            ]
            for mov in movements
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)
