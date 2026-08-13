from fastapi import APIRouter, Depends

from commons.auth import get_current_user
from commons.logger import get_logger
from core.apis.schemas.requests.auth_request import LoginRequest
from core.apis.schemas.responses.auth_response import TokenResponse
from core.apis.schemas.responses.user_response import UserMeResponse
from core.controllers.auth_controller import AuthController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])
auth_controller = AuthController()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Authenticates user credentials and issues a signed JWT access token.
    Validates email/password against stored bcrypt hashes.

    Args:
        login_data (LoginRequest): User email and password payload.

    Returns:
        TokenResponse: Access token and token header type.
    """
    logger.info("Calling POST /v1/auth/login endpoint")
    return await auth_controller.login(login_data)


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Retrieves identity, role, and permissions of the currently authenticated user.
    Requires a valid JWT Bearer Authorization header.

    Args:
        current_user (UserModel): Authenticated user dependency.

    Returns:
        UserMeResponse: Detailed user metadata and granted permissions.
    """
    logger.info(f"Calling GET /v1/auth/me endpoint for {current_user.email}")
    return await auth_controller.get_me(current_user)
