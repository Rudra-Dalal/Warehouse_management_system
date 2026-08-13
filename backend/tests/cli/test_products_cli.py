from unittest.mock import patch, MagicMock
import pytest
from cli.commands.products import (
    handle_products_list,
    handle_products_get,
    handle_products_sku,
    handle_products_upc,
    handle_products_scan,
)

@patch("cli.commands.products.make_request")
@patch("cli.commands.products.print_table")
def test_products_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "prod1",
            "sku": "SKU-VAL-001",
            "name": "Widget A",
            "upc": "001234567890",
            "seller_id": "seller1",
        }
    ]

    args = MagicMock()
    args.seller_id = "seller1"

    handle_products_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/products",
        query_params={"seller_id": "seller1"}
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.products.make_request")
@patch("cli.commands.products.print_object")
def test_products_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "prod1", "sku": "SKU-VAL-001"}
    args = MagicMock()
    args.product_id = "prod1"

    handle_products_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/products/prod1")
    mock_print_object.assert_called_once_with({"id": "prod1", "sku": "SKU-VAL-001"})

@patch("cli.commands.products.make_request")
@patch("cli.commands.products.print_object")
def test_products_sku(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "prod1", "sku": "SKU-VAL-001"}
    args = MagicMock()
    args.sku = "SKU-VAL-001"

    handle_products_sku(args)
    mock_make_request.assert_called_once_with("GET", "/v1/products/by-sku/SKU-VAL-001")
    mock_print_object.assert_called_once_with({"id": "prod1", "sku": "SKU-VAL-001"})

@patch("cli.commands.products.make_request")
@patch("cli.commands.products.print_object")
def test_products_upc_preserves_leading_zeros(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "prod1", "upc": "012345678905"}
    args = MagicMock()
    args.upc = "012345678905"

    handle_products_upc(args)
    # Ensure that string version with leading zeros is passed correctly
    mock_make_request.assert_called_once_with("GET", "/v1/products/by-upc/012345678905")
    mock_print_object.assert_called_once_with({"id": "prod1", "upc": "012345678905"})

@patch("cli.commands.products.make_request")
def test_products_scan_single_success(mock_make_request):
    mock_make_request.side_effect = [
        {"id": "prod1", "sku": "SKU-VAL-001", "name": "Widget A", "upc": "012345678905", "seller_id": "seller1", "is_active": True},
        [{"warehouse_code": "RENO", "available_quantity": 25}, {"warehouse_code": "COLUMBUS", "available_quantity": 12}]
    ]

    args = MagicMock()
    args.barcode = "012345678905"

    with patch("builtins.print") as mock_print:
        handle_products_scan(args)

    assert mock_make_request.call_count == 2
    mock_make_request.assert_any_call("GET", "/v1/products/by-upc/012345678905")
    mock_make_request.assert_any_call("GET", "/v1/inventory", query_params={"product_id": "prod1"})

    # Verify stdout outputs
    printed_output = "".join([call[0][0] if call[0] else "" for call in mock_print.call_args_list])
    assert "Widget A" in printed_output
    assert "SKU-VAL-001" in printed_output
    assert "RENO       : 25 available" in printed_output
    assert "COLUMBUS   : 12 available" in printed_output

@patch("cli.commands.products.make_request")
def test_products_scan_single_not_found(mock_make_request):
    from cli.client.api_client import APIError
    mock_make_request.side_effect = APIError(404, "Not Found")

    args = MagicMock()
    args.barcode = "999999999999"

    with patch("builtins.print") as mock_print, pytest.raises(SystemExit) as exc_info:
        handle_products_scan(args)

    assert exc_info.value.code == 1
    printed_output = "".join([call[0][0] if call[0] else "" for call in mock_print.call_args_list])
    assert "Barcode not found" in printed_output
    assert "UPC: 999999999999" in printed_output

@patch("cli.commands.products.make_request")
@patch("builtins.input", side_effect=["012345678905", "q"])
def test_products_scan_interactive_loop(mock_input, mock_make_request):
    mock_make_request.side_effect = [
        {"id": "prod1", "sku": "SKU-VAL-001", "name": "Widget A", "upc": "012345678905", "seller_id": "seller1", "is_active": True},
        [{"warehouse_code": "RENO", "available_quantity": 25}]
    ]

    args = MagicMock()
    args.barcode = None

    with patch("builtins.print") as mock_print:
        handle_products_scan(args)

    assert mock_make_request.call_count == 2
    printed_output = "".join([call[0][0] if call[0] else "" for call in mock_print.call_args_list])
    assert "Interactive Barcode" in printed_output
    assert "Widget A" in printed_output
    assert "Exiting scan mode" in printed_output

@patch("builtins.input", side_effect=KeyboardInterrupt)
def test_products_scan_interactive_ctrl_c(mock_input):
    args = MagicMock()
    args.barcode = None

    with patch("builtins.print") as mock_print:
        handle_products_scan(args)

    printed_output = "".join([call[0][0] if call[0] else "" for call in mock_print.call_args_list])
    assert "Exiting scan mode" in printed_output
