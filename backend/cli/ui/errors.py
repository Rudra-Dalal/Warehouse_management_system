import sys
from cli.client.api_client import APIError

def format_error(e: APIError) -> str:
    """Translates APIError into formatted, user-friendly CLI terminal output."""
    status_code = e.status_code
    detail = e.detail

    if status_code == 401:
        return (
            f"Authentication required or session expired.\n"
            f"Detail: {detail}\n\n"
            f"Please run:\n"
            f"  python -m cli login"
        )
    elif status_code == 403:
        return (
            f"Access Denied: You do not have permission for this operation.\n"
            f"Detail: {detail}"
        )
    elif status_code == 404:
        return (
            f"Resource Not Found: The requested resource does not exist.\n"
            f"Detail: {detail}"
        )
    elif status_code == 409:
        return (
            f"State Conflict: The operation conflicts with the current warehouse or order state.\n"
            f"Detail: {detail}"
        )
    elif status_code == 422:
        return (
            f"Validation Failed: Invalid request data was submitted.\n"
            f"Detail: {detail}"
        )
    elif status_code == 503:
        return (
            f"Service Unavailable: {detail}"
        )
    else:
        return f"Error [{status_code}]: {detail}"

def print_error_and_exit(e: APIError) -> None:
    """Prints translated API error text to stderr and terminates process with code 1."""
    print(format_error(e), file=sys.stderr)
    sys.exit(1)
