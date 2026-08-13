from unittest.mock import patch, MagicMock
from cli.commands.receiving import (
    handle_receiving_list,
    handle_receiving_get,
    handle_receiving_create,
)

@patch("cli.commands.receiving.make_request")
@patch("cli.commands.receiving.print_table")
def test_receiving_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "rec1",
            "receiving_reference": "REC-001",
            "warehouse_code": "RENO",
            "seller_id": "seller1",
            "created_at": "2026-08-13T12:00:00",
        }
    ]

    args = MagicMock()
    args.warehouse_code = "RENO"
    args.seller_id = "seller1"

    handle_receiving_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/receiving",
        query_params={"warehouse_code": "RENO", "seller_id": "seller1"}
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.receiving.make_request")
@patch("cli.commands.receiving.print_object")
def test_receiving_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "rec1", "receiving_reference": "REC-001"}
    args = MagicMock()
    args.receiving_id = "rec1"

    handle_receiving_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/receiving/rec1")
    mock_print_object.assert_called_once_with({"id": "rec1", "receiving_reference": "REC-001"})

@patch("cli.commands.receiving.make_request")
@patch("cli.commands.receiving.print_success")
def test_receiving_create(mock_print_success, mock_make_request):
    mock_make_request.return_value = {"id": "rec1", "receiving_reference": "REC-001"}
    
    args = MagicMock()
    args.reference = "REC-001"
    args.warehouse_code = "RENO"
    args.seller_id = "seller1"
    args.items = "prod1:10,prod2:20"

    handle_receiving_create(args)

    mock_make_request.assert_called_once_with(
        "POST",
        "/v1/receiving",
        body={
            "receiving_reference": "REC-001",
            "warehouse_code": "RENO",
            "seller_id": "seller1",
            "items": [
                {"product_id": "prod1", "quantity": 10},
                {"product_id": "prod2", "quantity": 20}
            ]
        }
    )
    mock_print_success.assert_called_once()
