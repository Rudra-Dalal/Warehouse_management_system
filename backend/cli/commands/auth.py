import sys
import getpass
from cli.client.api_client import make_request, APIError
from cli.client.auth_client import save_session, clear_session, get_token
from cli.ui.output import print_success, print_object
from cli.ui.errors import print_error_and_exit

def handle_login(args) -> None:
    """Prompts for credentials, authenticates with the backend, and saves the JWT token."""
    # Obtain inputs
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    if not email or not password:
        print("Error: Email and password are required.", file=sys.stderr)
        sys.exit(1)

    try:
        # Post credentials to backend login endpoint
        login_res = make_request(
            "POST",
            "/v1/auth/login",
            body={"email": email, "password": password}
        )
        token = login_res.get("access_token")

        # Set session temporarily to request /v1/auth/me
        save_session(token)

        # Retrieve current user's profile metadata and permissions
        me_res = make_request("GET", "/v1/auth/me")

        # Save session persistently with user metadata
        save_session(token, me_res)

        print_success("Login successful!", me_res)
    except APIError as e:
        clear_session()
        print_error_and_exit(e)

def handle_logout(args) -> None:
    """Removes the cached JWT token and clears the local login session."""
    clear_session()
    print_success("Logged out successfully.")

def handle_whoami(args) -> None:
    """Queries the backend for the current user's active session details."""
    token = get_token()
    if not token:
        print("Not logged in. Please login first:\n  python -m cli login")
        return

    try:
        me_res = make_request("GET", "/v1/auth/me")
        print_object(me_res)
    except APIError as e:
        print_error_and_exit(e)
