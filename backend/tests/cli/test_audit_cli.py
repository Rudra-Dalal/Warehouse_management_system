from unittest.mock import patch, MagicMock
from cli.commands.audit import (
    handle_audit_list,
    handle_audit_get,
    handle_audit_entity,
    handle_audit_user,
)

@patch("cli.commands.audit.make_request")
@patch("cli.commands.audit.print_table")
def test_audit_list(mock_print_table, mock_make_request):
    mock_make_request.return_value = [
        {
            "id": "aud1",
            "action": "CREATE",
            "entity_type": "PRODUCT",
            "entity_id": "prod1",
            "user_id": "user1",
            "success": True,
            "created_at": "2026-08-13T10:00:00",
        }
    ]

    args = MagicMock()
    args.action = "CREATE"
    args.entity_type = "PRODUCT"
    args.entity_id = "prod1"
    args.user_id = "user1"
    args.warehouse_code = "RENO"
    args.reference_type = None
    args.reference_id = None
    args.success = True
    args.limit = 50
    args.offset = 0

    handle_audit_list(args)

    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/audit",
        query_params={
            "action": "CREATE",
            "entity_type": "PRODUCT",
            "entity_id": "prod1",
            "user_id": "user1",
            "warehouse_code": "RENO",
            "reference_type": None,
            "reference_id": None,
            "success": True,
            "limit": 50,
            "offset": 0,
        }
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.audit.make_request")
@patch("cli.commands.audit.print_object")
def test_audit_get(mock_print_object, mock_make_request):
    mock_make_request.return_value = {"id": "aud1", "action": "CREATE"}
    args = MagicMock()
    args.audit_id = "aud1"

    handle_audit_get(args)
    mock_make_request.assert_called_once_with("GET", "/v1/audit/aud1")
    mock_print_object.assert_called_once_with({"id": "aud1", "action": "CREATE"})

@patch("cli.commands.audit.make_request")
@patch("cli.commands.audit.print_table")
def test_audit_entity(mock_print_table, mock_make_request):
    mock_make_request.return_value = [{"id": "aud1", "action": "CREATE"}]
    args = MagicMock()
    args.entity_type = "PRODUCT"
    args.entity_id = "prod1"
    args.limit = 50
    args.offset = 0

    handle_audit_entity(args)
    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/audit/entity/PRODUCT/prod1",
        query_params={"limit": 50, "offset": 0}
    )
    mock_print_table.assert_called_once()

@patch("cli.commands.audit.make_request")
@patch("cli.commands.audit.print_table")
def test_audit_user(mock_print_table, mock_make_request):
    mock_make_request.return_value = [{"id": "aud1", "action": "CREATE"}]
    args = MagicMock()
    args.user_id = "user1"
    args.limit = 50
    args.offset = 0

    handle_audit_user(args)
    mock_make_request.assert_called_once_with(
        "GET",
        "/v1/audit/user/user1",
        query_params={"limit": 50, "offset": 0}
    )
    mock_print_table.assert_called_once()
