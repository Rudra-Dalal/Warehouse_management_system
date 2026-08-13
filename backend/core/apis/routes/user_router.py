from typing import List
from fastapi import APIRouter, Depends, status

from commons.auth import get_current_user, require_permission
from commons.logger import get_logger
from core.apis.schemas.requests.user_request import UserCreateRequest, UserUpdateRequest
from core.apis.schemas.responses.user_response import UserResponse
from core.controllers.user_controller import UserController
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/users", tags=["Users"])
user_controller = UserController()


@router.get("", response_model=List[UserResponse])
async def list_users(
    current_user: UserModel = Depends(require_permission("users.manage")),
):
    """Lists all user accounts in the system.
    Requires 'users.manage' permission.

    Args:
        current_user (UserModel): Authenticated administrator.

    Returns:
        List[UserResponse]: List of all registered users.
    """
    logger.info(f"Calling GET /v1/users endpoint by {current_user.email}")
    return await user_controller.list_users()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: UserModel = Depends(require_permission("users.manage")),
):
    """Creates a new user account with specified role assignment.
    Requires 'users.manage' permission.

    Args:
        request (UserCreateRequest): User creation parameters.
        current_user (UserModel): Authenticated administrator.

    Returns:
        UserResponse: The newly created user details.
    """
    logger.info(f"Calling POST /v1/users endpoint by {current_user.email}")
    return await user_controller.create_user(request, current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieves user account details by ObjectId string.
    Requires a valid authenticated JWT user token.

    Args:
        user_id (str): Target user ObjectId string.
        current_user (UserModel): Authenticated user.

    Returns:
        UserResponse: Public user details response.
    """
    logger.info(f"Calling GET /v1/users/{user_id} endpoint by {current_user.email}")
    return await user_controller.get_user_by_id(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Updates user account details or role assignment.
    Requires 'users.manage' permission if attempting to modify role or active status.

    Args:
        user_id (str): Target user ObjectId string.
        request (UserUpdateRequest): Field updates.
        current_user (UserModel): Authenticated user requesting update.

    Returns:
        UserResponse: Updated user details response.
    """
    logger.info(f"Calling PATCH /v1/users/{user_id} endpoint by {current_user.email}")
    return await user_controller.update_user(user_id, request, current_user)
