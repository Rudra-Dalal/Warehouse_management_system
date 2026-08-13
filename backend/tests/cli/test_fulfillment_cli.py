from unittest.mock import patch, MagicMock
from cli.commands.fulfillment import (
    handle_fulfillment_list,
    handle_fulfillment_get,
    handle_fulfillment_create,
    handle_fulfillment_pick,
    handle_fulfillment_pack,
    handle_fulfillment_ship,
)

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_table")
def test_fulfillment_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {"id": "ful1", "order_id": "order1", "warehouse_code": "RENO", "status": "READY_TO_PICK"}
    ]
    args = MagicMock()
    args.warehouse_code = "RENO"
    args.status = "READY_TO_PICK"

    handle_fulfillment_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/fulfillment",
        query_params={"warehouse_code": "RENO", "status": "READY_TO_PICK"}
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_object")
def test_fulfillment_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "ful1", "status": "READY_TO_PICK"}
    args = MagicMock()
    args.fulfillment_id = "ful1"

    handle_fulfillment_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/fulfillment/ful1")
    mock_print_object.assert_called_once_with({"id": "ful1", "status": "READY_TO_PICK"})

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_success")
def test_fulfillment_create(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "ful1", "status": "READY_TO_PICK"}
    args = MagicMock()
    args.order_id = "order1"

    handle_fulfillment_create(args)
    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/fulfillment",
        body={"order_id": "order1"}
    )
    mock_print_success.assert_called_once()

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_success")
def test_fulfillment_pick(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "ful1", "status": "PICKED"}
    args = MagicMock()
    args.fulfillment_id = "ful1"
    args.items = "prod1:5,prod2:10"

    handle_fulfillment_pick(args)
    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/fulfillment/ful1/pick",
        body={
            "items": [
                {"product_id": "prod1", "quantity": 5},
                {"product_id": "prod2", "quantity": 10}
            ]
        }
    )
    mock_print_success.assert_called_once()

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_success")
def test_fulfillment_pack(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "ful1", "status": "PACKED"}
    args = MagicMock()
    args.fulfillment_id = "ful1"
    args.note = "Box size #3"

    handle_fulfillment_pack(args)
    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/fulfillment/ful1/pack",
        body={"note": "Box size #3"}
    )
    mock_print_success.assert_called_once()

@patch("cli.commands.fulfillment.make_request")
@patch("cli.commands.fulfillment.print_success")
def test_fulfillment_ship(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "ful1", "status": "SHIPPED"}
    args = MagicMock()
    args.fulfillment_id = "ful1"
    args.tracking = "TRK123456"

    handle_fulfillment_ship(args)
    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/fulfillment/ful1/ship",
        body={"tracking_number": "TRK123456"}
    )
    mock_print_success.assert_called_once()
