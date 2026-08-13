from unittest.mock import patch, MagicMock
import pytest
from cli.commands.auth import handle_login, handle_logout, handle_whoami
from cli.client.auth_client import get_token, clear_session

@patch("cli.commands.auth.make_request")
@patch("cli.commands.auth.save_session")
@patch("builtins.input", side_effect=["test@example.com"])
@patch("getpass.getpass", return_value="SecretPassword123")
def test_handle_login_success(
    mock_getpass, mock_input, mock_save_session, mock_make_request
):
    # Mock responses for POST /v1/auth/login and GET /v1/auth/me
    mock_make_request.side_effect = [
        {"access_token": "mock-jwt-token"},
        {"email": "test@example.com", "role": "ADMIN", "permissions": ["users.manage"]}
    ]

    args = MagicMock()
    handle_login(args)

    assert mock_make_request.call_count == 2
    mock_save_session.assert_any_call("mock-jwt-token")
    mock_save_session.assert_any_call(
        "mock-jwt-token",
        {"email": "test@example.com", "role": "ADMIN", "permissions": ["users.manage"]}
    )

@patch("cli.commands.auth.clear_session")
def test_handle_logout(mock_clear_session):
    args = MagicMock()
    handle_logout(args)
    mock_clear_session.assert_called_once()

@patch("cli.commands.auth.get_token", return_value="mock-jwt-token")
@patch("cli.commands.auth.make_request")
@patch("cli.commands.auth.print_object")
def test_handle_whoami_logged_in(
    mock_print_object, mock_make_request, mock_get_token
):
    mock_make_request.return_value = {"email": "test@example.com", "role": "ADMIN"}
    args = MagicMock()
    handle_whoami(args)

    mock_make_request.assert_called_once_with("GET", "/v1/auth/me")
    mock_print_object.assert_called_once_with({"email": "test@example.com", "role": "ADMIN"})

@patch("cli.commands.auth.get_token", return_value="")
def test_handle_whoami_logged_out(mock_get_token):
    with patch("builtins.print") as mock_print:
        args = MagicMock()
        handle_whoami(args)
        mock_print.assert_called_once()
        assert "Not logged in" in mock_print.call_args[0][0]
