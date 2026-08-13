from unittest.mock import patch, MagicMock
from cli.commands.orders import (
    handle_orders_list,
    handle_orders_get,
    handle_orders_create,
)

@patch("cli.commands.orders.make_request")
@patch("cli.commands.orders.print_table")
def test_orders_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "order1",
            "order_number": "ORD-001",
            "warehouse_code": "RENO",
            "seller_id": "seller1",
            "status": "CONFIRMED",
        }
    ]

    args = MagicMock()
    args.warehouse_code = "RENO"
    args.seller_id = "seller1"
    args.status = "CONFIRMED"

    handle_orders_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/orders",
        query_params={
            "warehouse_code": "RENO",
            "seller_id": "seller1",
            "status": "CONFIRMED",
        }
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.orders.make_request")
@patch("cli.commands.orders.print_object")
def test_orders_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "order1", "order_number": "ORD-001"}
    args = MagicMock()
    args.order_id = "order1"

    handle_orders_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/orders/order1")
    mock_print_object.assert_called_once_with({"id": "order1", "order_number": "ORD-001"})

@patch("cli.commands.orders.make_request")
@patch("cli.commands.orders.print_success")
def test_orders_create(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "order1", "order_number": "ORD-001"}
    
    args = MagicMock()
    args.order_number = "ORD-001"
    args.warehouse_code = "RENO"
    args.seller_id = "seller1"
    args.items = "prod1:10,prod2:20"

    handle_orders_create(args)

    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/orders",
        body={
            "order_number": "ORD-001",
            "warehouse_code": "RENO",
            "seller_id": "seller1",
            "items": [
                {"product_id": "prod1", "quantity": 10},
                {"product_id": "prod2", "quantity": 20}
            ]
        }
    )
    mock_print_success.assert_called_once()
