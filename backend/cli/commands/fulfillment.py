import sys
from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object, print_success
from cli.ui.errors import print_error_and_exit

def handle_fulfillment_list(args) -> None:
    """Lists operational fulfillment execution records."""
    try:
        query_params = {}
        if args.warehouse_code:
            query_params["warehouse_code"] = args.warehouse_code
        if args.status:
            query_params["status"] = args.status

        fulfillments = make_request("GET", "/v1/fulfillment", query_params=query_params)
        headers = ["ID", "Order ID", "Warehouse Code", "Status"]
        rows = [
            [
                f.get("id"),
                f.get("order_id"),
                f.get("warehouse_code"),
                f.get("status"),
            ]
            for f in fulfillments
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_fulfillment_get(args) -> None:
    """Retrieves a fulfillment execution record by ObjectId string."""
    try:
        fulfillment = make_request("GET", f"/v1/fulfillment/{args.fulfillment_id}")
        print_object(fulfillment)
    except APIError as e:
        print_error_and_exit(e)

def handle_fulfillment_create(args) -> None:
    """Initiates a fulfillment execution task for a CONFIRMED order."""
    try:
        body = {"order_id": args.order_id.strip()}
        res = make_request("POST", "/v1/fulfillment", body=body)
        print_success("Fulfillment task initiated successfully.", res)
    except APIError as e:
        print_error_and_exit(e)

def handle_fulfillment_pick(args) -> None:
    """Executes picking operation for a READY_TO_PICK fulfillment."""
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

    body = {"items": items}
    try:
        res = make_request("POST", f"/v1/fulfillment/{args.fulfillment_id}/pick", body=body)
        print_success("Picking completed successfully.", res)
    except APIError as e:
        print_error_and_exit(e)

def handle_fulfillment_pack(args) -> None:
    """Executes packing operation for a PICKED fulfillment task."""
    try:
        body = {"note": args.note}
        res = make_request("POST", f"/v1/fulfillment/{args.fulfillment_id}/pack", body=body)
        print_success("Packing completed successfully.", res)
    except APIError as e:
        print_error_and_exit(e)

def handle_fulfillment_ship(args) -> None:
    """Executes shipping operation for a PACKED fulfillment task."""
    try:
        body = {"tracking_number": args.tracking}
        res = make_request("POST", f"/v1/fulfillment/{args.fulfillment_id}/ship", body=body)
        print_success("Fulfillment task shipped successfully.", res)
    except APIError as e:
        print_error_and_exit(e)
