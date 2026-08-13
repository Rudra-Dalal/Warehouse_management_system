from unittest.mock import patch, MagicMock
from cli.commands.inventory import (
    handle_inventory_list,
    handle_inventory_get,
    handle_inventory_adjust,
    handle_inventory_reserve,
    handle_inventory_movements,
)

@patch("cli.commands.inventory.make_request")
@patch("cli.commands.inventory.print_table")
def test_inventory_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "inv1",
            "product_id": "prod1",
            "sku": "SKU1",
            "warehouse_code": "RENO",
            "available_quantity": 10,
            "reserved_quantity": 2,
            "damaged_quantity": 0,
        }
    ]

    args = MagicMock()
    args.warehouse_code = "RENO"
    args.sku = None
    args.product_id = None

    handle_inventory_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/inventory",
        query_params={"warehouse_code": "RENO"}
    )
    mock_print_table.assert_called_once()
    headers = mock_print_table.call_args[0][0]
    rows = mock_print_table.call_args[0][1]
    assert "Available" in headers
    assert rows[0][2] == "SKU1"

@patch("cli.commands.inventory.make_request")
@patch("cli.commands.inventory.print_object")
def test_inventory_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "inv-obj-id", "sku": "SKU1"}

    args = MagicMock()
    args.inventory_id = "inv-obj-id"

    handle_inventory_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/inventory/inv-obj-id")
    mock_print_object.assert_called_once_with({"id": "inv-obj-id", "sku": "SKU1"})

@patch("cli.commands.inventory.make_request")
@patch("cli.commands.inventory.print_success")
def test_inventory_adjust(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "inv-obj-id", "available_quantity": 15}

    args = MagicMock()
    args.inventory_id = "inv-obj-id"
    args.quantity = 5
    args.note = "Cycle count adjustment"

    handle_inventory_adjust(args)
    mock_make_request.assert_called_once_with(
        "PATCH",
        "/v1/inventory/inv-obj-id/adjust",
        body={"quantity_delta": 5, "note": "Cycle count adjustment"}
    )
    mock_print_success.assert_called_once()

@patch("cli.commands.inventory.make_request")
@patch("cli.commands.inventory.print_success")
def test_inventory_reserve(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "inv-obj-id", "reserved_quantity": 5}

    args = MagicMock()
    args.inventory_id = "inv-obj-id"
    args.quantity = 5

    handle_inventory_reserve(args)
    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/inventory/inv-obj-id/reserve",
        body={"quantity": 5}
    )
    mock_print_success.assert_called_once()

@patch("cli.commands.inventory.make_request")
@patch("cli.commands.inventory.print_table")
def test_inventory_movements(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "mov1",
            "movement_type": "IN",
            "quantity": 10,
            "reference_type": "RECEIVING",
            "user_id": "user1",
            "created_at": "2026-08-13T10:00:00",
        }
    ]

    args = MagicMock()
    args.inventory_id = "inv-obj-id"

    handle_inventory_movements(args)
    mock_make_request.assert_called_once_with("GET", "/v1/inventory/inv-obj-id/movements")
    mock_print_table.assert_called_once()
