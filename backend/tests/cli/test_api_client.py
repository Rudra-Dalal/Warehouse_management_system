import json
import urllib.error
from unittest.mock import patch, MagicMock
import pytest

from cli.client.api_client import make_request, APIError
from cli.client import auth_client

@patch("urllib.request.urlopen")
def test_make_request_get_success(mock_urlopen):
    # Mock successful JSON response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "healthy"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = make_request("GET", "/health")
    assert res == {"status": "healthy"}
    mock_urlopen.assert_called_once()
    
    # Check request URL
    req_arg = mock_urlopen.call_args[0][0]
    assert req_arg.get_full_url() == "http://127.0.0.1:8000/health"
    assert req_arg.get_method() == "GET"

@patch("urllib.request.urlopen")
def test_make_request_post_with_body_and_token(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": "123"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Inject mock token
    with patch("cli.client.api_client.get_token", return_value="mock-jwt-token"):
        res = make_request("POST", "/v1/orders", body={"order_number": "1"})
        
    assert res == {"id": "123"}
    req_arg = mock_urlopen.call_args[0][0]
    assert req_arg.get_full_url() == "http://127.0.0.1:8000/v1/orders"
    assert req_arg.get_method() == "POST"
    assert req_arg.get_header("Content-type") == "application/json"
    assert req_arg.get_header("Authorization") == "Bearer mock-jwt-token"
    assert req_arg.data == b'{"order_number": "1"}'

@patch("urllib.request.urlopen")
def test_make_request_http_error_parsing(mock_urlopen):
    # Mock an HTTP 409 error
    mock_err_fp = MagicMock()
    mock_err_fp.read.return_value = b'{"detail": "Insufficient stock"}'
    
    http_error = urllib.error.HTTPError(
        url="http://test",
        code=409,
        msg="Conflict",
        hdrs=None,
        fp=mock_err_fp
    )
    mock_urlopen.side_effect = http_error

    with pytest.raises(APIError) as exc_info:
        make_request("POST", "/v1/orders")
        
    assert exc_info.value.status_code == 409
    assert "Insufficient stock" in exc_info.value.detail

@patch("urllib.request.urlopen")
def test_make_request_connection_failure(mock_urlopen):
    # Mock a connection URL error (server down)
    url_error = urllib.error.URLError(reason="Connection refused")
    mock_urlopen.side_effect = url_error

    with pytest.raises(APIError) as exc_info:
        make_request("GET", "/health")
        
    assert exc_info.value.status_code == 503
    assert "Connection refused" in exc_info.value.detail
