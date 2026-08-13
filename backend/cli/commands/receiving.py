import sys
from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object, print_success
from cli.ui.errors import print_error_and_exit

def handle_receiving_list(args) -> None:
    """Lists receiving shipments filtered by warehouse code or seller ID."""
    try:
        query_params = {}
        if args.warehouse_code:
            query_params["warehouse_code"] = args.warehouse_code
        if args.seller_id:
            query_params["seller_id"] = args.seller_id

        receivings = make_request("GET", "/v1/receiving", query_params=query_params)
        headers = ["ID", "Reference", "Warehouse Code", "Seller ID", "Created At"]
        rows = [
            [
                r.get("id"),
                r.get("receiving_reference"),
                r.get("warehouse_code"),
                r.get("seller_id"),
                r.get("created_at"),
            ]
            for r in receivings
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_receiving_get(args) -> None:
    """Retrieves details for a specific receiving shipment by string ObjectId."""
    try:
        receiving = make_request("GET", f"/v1/receiving/{args.receiving_id}")
        print_object(receiving)
    except APIError as e:
        print_error_and_exit(e)

def handle_receiving_create(args) -> None:
    """Creates a new inbound receiving shipment with items parsed as product_id:quantity."""
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
        "receiving_reference": args.reference.strip(),
        "warehouse_code": args.warehouse_code.upper().strip(),
        "seller_id": args.seller_id.strip(),
        "items": items
    }

    try:
        receiving = make_request("POST", "/v1/receiving", body=body)
        print_success("Receiving shipment created successfully.", receiving)
    except APIError as e:
        print_error_and_exit(e)
