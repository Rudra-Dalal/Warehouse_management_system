import urllib.request
import urllib.error
import urllib.parse
import json
from typing import Any, Dict, Optional
from cli.config import API_BASE_URL
from cli.client.auth_client import get_token

class APIError(Exception):
    """Exception raised when an API request fails."""
    def __init__(self, status_code: int, detail: str, raw_response: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.raw_response = raw_response
        super().__init__(f"HTTP {status_code}: {detail}")

def make_request(
    method: str,
    path: str,
    query_params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None
) -> Any:
    """Performs an HTTP request using urllib.request and returns the parsed JSON response.
    Automatically handles JWT bearer token injection and parses backend API errors.
    """
    path = path.lstrip("/")
    url = f"{API_BASE_URL}/{path}"

    if query_params:
        # Filter None and convert bools to string lowercase
        clean_params = {}
        for k, v in query_params.items():
            if v is not None:
                if isinstance(v, bool):
                    clean_params[k] = str(v).lower()
                else:
                    clean_params[k] = str(v)
        if clean_params:
            url = f"{url}?{urllib.parse.urlencode(clean_params)}"

    data = None
    headers = {
        "Accept": "application/json",
    }

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    token = get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method.upper()
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            if not res_data:
                return {}
            return json.loads(res_data)
    except urllib.error.HTTPError as e:
        try:
            err_data = e.read().decode("utf-8")
            err_json = json.loads(err_data)
            detail = err_json.get("detail", str(e))
            
            # Format validation errors nicely
            if isinstance(detail, list):
                parts = []
                for error_item in detail:
                    loc = " -> ".join(str(x) for x in error_item.get("loc", []))
                    msg = error_item.get("msg", "")
                    parts.append(f"[{loc}]: {msg}")
                detail_str = ", ".join(parts)
                raise APIError(e.code, detail_str, err_data)
            
            raise APIError(e.code, str(detail), err_data)
        except APIError:
            raise
        except Exception:
            raise APIError(e.code, e.reason or str(e))
    except urllib.error.URLError as e:
        raise APIError(503, f"Connection to WMS API failed: {e.reason}")
    except Exception as e:
        raise APIError(500, f"Unexpected error: {str(e)}")
