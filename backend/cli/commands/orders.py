import sys
from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object, print_success
from cli.ui.errors import print_error_and_exit

def handle_orders_list(args) -> None:
    """Lists customer orders with optional warehouse, seller, or status filtering."""
    try:
        query_params = {}
        if args.warehouse_code:
            query_params["warehouse_code"] = args.warehouse_code
        if args.seller_id:
            query_params["seller_id"] = args.seller_id
        if args.status:
            # Query param uses status alias
            query_params["status"] = args.status

        orders = make_request("GET", "/v1/orders", query_params=query_params)
        headers = ["ID", "Order Number", "Warehouse Code", "Seller ID", "Status"]
        rows = [
            [
                o.get("id"),
                o.get("order_number"),
                o.get("warehouse_code"),
                o.get("seller_id"),
                o.get("status"),
            ]
            for o in orders
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_orders_get(args) -> None:
    """Retrieves detailed information for a specific customer order by string ObjectId."""
    try:
        order = make_request("GET", f"/v1/orders/{args.order_id}")
        print_object(order)
    except APIError as e:
        print_error_and_exit(e)

def handle_orders_create(args) -> None:
    """Creates a customer order, registering and confirming via backend transaction."""
    items = []
    for item_str in args.items.split(","):
        item_str = item_str.strip()
        if not item_str:
            continue
        parts = item_str.split(":")
        if len(parts) != 2:
            print(
                "Error: Items format must be product_id:quantity (e.g. ID:10,ID2:20)",
                file=sys.stderr
            )
            sys.exit(1)
        product_id, qty_str = parts
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError()
        except ValueError:
            print(
                f"Error: Quantity must be a positive integer, got '{qty_str}'",
                file=sys.stderr
            )
            sys.exit(1)
        items.append({
            "product_id": product_id.strip(),
            "quantity": qty
        })

    body = {
        "order_number": args.order_number.strip(),
        "warehouse_code": args.warehouse_code.upper().strip(),
        "seller_id": args.seller_id.strip(),
        "items": items
    }

    try:
        order = make_request("POST", "/v1/orders", body=body)
        print_success("Order created and confirmed successfully.", order)
    except APIError as e:
        print_error_and_exit(e)
