from fastapi import HTTPException, status

from commons.logger import get_logger
from commons.security import create_access_token, verify_password
from core.apis.schemas.requests.auth_request import LoginRequest
from core.apis.schemas.responses.auth_response import TokenResponse
from core.apis.schemas.responses.user_response import UserMeResponse
from core.cruds.permission_crud import PermissionCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel

logger = get_logger(__name__)


class AuthController:
    """Business logic controller orchestrating user authentication and JWT operations.
    Handles credential validation, password verification, and session state resolution.
    """

    def __init__(self):
        """Initializes AuthController with User, Role, and Permission CRUD instances."""
        self.user_crud = UserCRUD()
        self.role_crud = RoleCRUD()
        self.permission_crud = PermissionCRUD()

    async def login(self, login_data: LoginRequest) -> TokenResponse:
        """Validates user login credentials and returns a signed JWT access token.
        Raises HTTP 401 for unknown email, incorrect password, or disabled user.

        Args:
            login_data (LoginRequest): The login credentials payload.

        Returns:
            TokenResponse: The generated JWT access token payload.
        """
        logger.info(f"Executing AuthController.login for {login_data.email}")
        user = await self.user_crud.get_by_email(login_data.email)
        if not user:
            logger.warning(f"Login failed: Unknown email {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not user.is_active:
            logger.warning(f"Login failed: User account {login_data.email} is disabled")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        if not verify_password(login_data.password, user.password_hash):
            logger.warning(f"Login failed: Password mismatch for {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        access_token = create_access_token(subject=user.id)
        logger.info(f"Login successful for user {user.email}")
        return TokenResponse(access_token=access_token)

    async def get_me(self, current_user: UserModel) -> UserMeResponse:
        """Assembles detailed metadata payload for the current authenticated user.
        Resolves assigned security role name and granted permission strings.

        Args:
            current_user (UserModel): Active authenticated user instance.

        Returns:
            UserMeResponse: Current user metadata response.
        """
        logger.info(f"Executing AuthController.get_me for user {current_user.email}")
        role = await self.role_crud.get_by_id(current_user.role_id)
        permission_names = []
        role_name = None

        if role:
            role_name = role.name
            permissions = await self.permission_crud.get_by_ids(role.permission_ids)
            permission_names = [p.name for p in permissions]

        return UserMeResponse(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=role_name,
            permissions=permission_names,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )
