from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object
from cli.ui.errors import print_error_and_exit

def handle_products_list(args) -> None:
    """Lists registered products, optionally filtered by seller ID."""
    try:
        query_params = {}
        if args.seller_id:
            query_params["seller_id"] = args.seller_id
        
        products = make_request("GET", "/v1/products", query_params=query_params)
        headers = ["ID", "SKU", "Name", "UPC", "Seller ID"]
        rows = [
            [
                p.get("id"),
                p.get("sku"),
                p.get("name"),
                p.get("upc"),
                p.get("seller_id"),
            ]
            for p in products
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_products_get(args) -> None:
    """Retrieves product catalog details by ObjectId string."""
    try:
        product = make_request("GET", f"/v1/products/{args.product_id}")
        print_object(product)
    except APIError as e:
        print_error_and_exit(e)

def handle_products_sku(args) -> None:
    """Looks up a product by unique SKU business identifier."""
    try:
        product = make_request("GET", f"/v1/products/by-sku/{args.sku}")
        print_object(product)
    except APIError as e:
        print_error_and_exit(e)

def handle_products_upc(args) -> None:
    """Resolves a product by UPC barcode string (preserving leading zeros)."""
    # Ensure UPC remains strictly a string
    upc_str = str(args.upc).strip()
    try:
        product = make_request("GET", f"/v1/products/by-upc/{upc_str}")
        print_object(product)
    except APIError as e:
        print_error_and_exit(e)

import sys

def resolve_and_print_barcode(barcode_str: str) -> None:
    """Queries the backend to resolve the UPC string and queries stock levels."""
    # Query product details
    product = make_request("GET", f"/v1/products/by-upc/{barcode_str}")

    print("\nProduct Found")
    print("-------------------------")
    print(f"Name:       {product.get('name')}")
    print(f"SKU:        {product.get('sku')}")
    print(f"UPC:        {product.get('upc')}")
    print(f"Seller:     {product.get('seller_id')}")
    print(f"Status:     {'ACTIVE' if product.get('is_active') else 'INACTIVE'}")

    # Query inventory levels for the product
    inventory_list = make_request("GET", "/v1/inventory", query_params={"product_id": product.get("id")})

    print("\nInventory")
    print("-------------------------")
    if inventory_list:
        for warehouse_code in ["RENO", "COLUMBUS"]:
            matching = [inv for inv in inventory_list if inv.get("warehouse_code") == warehouse_code]
            if matching:
                inv = matching[0]
                available = inv.get("available_quantity", 0)
                print(f"{warehouse_code:<11}: {available} available")
            else:
                print(f"{warehouse_code:<11}: 0 available")
    else:
        print("RENO       : 0 available")
        print("COLUMBUS   : 0 available")

def handle_products_scan(args) -> None:
    """MVP scan abstraction. Resolves product by string barcode input.
    Supports single-scan or interactive loop scanning.
    """
    if args.barcode:
        barcode_str = str(args.barcode).strip()
        try:
            resolve_and_print_barcode(barcode_str)
        except APIError as e:
            if e.status_code == 404:
                print(f"\nBarcode not found.\n\nUPC: {barcode_str}\n\nPlease verify the barcode or product master data.")
                sys.exit(1)
            else:
                print_error_and_exit(e)
    else:
        print("WMS Barcode Scanner")
        print("-------------------")
        print("Interactive Barcode Scan Mode. Type 'q' or press Ctrl+C to exit.\n")
        while True:
            try:
                barcode_input = input("Scan barcode: ").strip()
                if barcode_input.lower() == 'q':
                    print("Exiting scan mode.")
                    break
                if not barcode_input:
                    continue

                try:
                    resolve_and_print_barcode(barcode_input)
                    print()
                except APIError as e:
                    if e.status_code == 404:
                        print(f"\nBarcode not found.\n\nUPC: {barcode_input}\n\nPlease verify the barcode or product master data.\n")
                    else:
                        from cli.ui.errors import format_error
                        print(f"\nScan Error: {format_error(e)}\n")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting scan mode.")
                break

