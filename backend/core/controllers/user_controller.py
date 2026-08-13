from typing import List
from fastapi import HTTPException, status

from commons.logger import get_logger
from commons.security import hash_password
from core.apis.schemas.requests.user_request import UserCreateRequest, UserUpdateRequest
from core.apis.schemas.responses.user_response import UserResponse
from core.cruds.permission_crud import PermissionCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel

logger = get_logger(__name__)


class UserController:
    """Business logic controller handling user profile and account management.
    Validates email uniqueness, role existence, password hashing, and privilege constraints.
    """

    def __init__(self):
        """Initializes UserController with User, Role, and Permission CRUD instances."""
        self.user_crud = UserCRUD()
        self.role_crud = RoleCRUD()
        self.permission_crud = PermissionCRUD()

    async def list_users(self) -> List[UserResponse]:
        """Retrieves all user accounts in the system.
        Returns a list of public UserResponse schemas.

        Returns:
            List[UserResponse]: List of all user accounts.
        """
        logger.info("Executing UserController.list_users")
        users = await self.user_crud.list_users()
        return [
            UserResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                role_id=u.role_id,
                is_active=u.is_active,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            for u in users
        ]

    async def get_user_by_id(self, user_id: str) -> UserResponse:
        """Retrieves a specific user account by string ObjectId.
        Raises HTTP 404 Not Found if no user exists.

        Args:
            user_id (str): Target user ObjectId string.

        Returns:
            UserResponse: Target user account details.
        """
        logger.info(f"Executing UserController.get_user_by_id for {user_id}")
        user = await self.user_crud.get_by_id(user_id)
        if not user:
            logger.warning(f"User ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role_id=user.role_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def create_user(
        self, request: UserCreateRequest, current_user: UserModel
    ) -> UserResponse:
        """Creates a new user account with hashed password and assigned security role.
        Raises HTTP 400 for invalid role or HTTP 409 for duplicate email.

        Args:
            request (UserCreateRequest): User creation payload.
            current_user (UserModel): Authenticated administrator executing creation.

        Returns:
            UserResponse: The created user account details.
        """
        logger.info(f"Executing UserController.create_user for {request.email}")
        role = await self.role_crud.get_by_id(request.role_id)
        if not role:
            logger.warning(f"User creation failed: Role ID {request.role_id} does not exist")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned role ID '{request.role_id}' does not exist",
            )

        existing = await self.user_crud.get_by_email(request.email)
        if existing:
            logger.warning(f"User creation failed: Email {request.email} already registered")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{request.email}' already exists",
            )

        password_hash_str = hash_password(request.password)
        new_user = UserModel(
            name=request.name,
            email=request.email,
            password_hash=password_hash_str,
            role_id=request.role_id,
            is_active=True,
        )
        created_user = await self.user_crud.create_user(new_user)
        logger.info(f"User {created_user.email} successfully created by {current_user.email}")
        return UserResponse(
            id=created_user.id,
            name=created_user.name,
            email=created_user.email,
            role_id=created_user.role_id,
            is_active=created_user.is_active,
            created_at=created_user.created_at,
            updated_at=created_user.updated_at,
        )

    async def update_user(
        self, target_user_id: str, request: UserUpdateRequest, current_user: UserModel
    ) -> UserResponse:
        """Updates profile, active status, or role assignment of a user account.
        Enforces privilege escalation check prohibiting non-managers from modifying roles.

        Args:
            target_user_id (str): Target user ObjectId string.
            request (UserUpdateRequest): Field update payload.
            current_user (UserModel): Authenticated user requesting update.

        Returns:
            UserResponse: The updated user account details.
        """
        logger.info(f"Executing UserController.update_user for target {target_user_id} by {current_user.email}")
        target_user = await self.user_crud.get_by_id(target_user_id)
        if not target_user:
            logger.warning(f"User update failed: Target user ID {target_user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{target_user_id}' not found",
            )

        # Privilege escalation check: if role_id or is_active is modified by a user without users.manage
        if request.role_id is not None or request.is_active is not None:
            # Check if current user possesses users.manage
            caller_role = await self.role_crud.get_by_id(current_user.role_id)
            caller_permissions = []
            if caller_role:
                perms = await self.permission_crud.get_by_ids(caller_role.permission_ids)
                caller_permissions = [p.name for p in perms]

            if "users.manage" not in caller_permissions:
                logger.warning(
                    f"Privilege escalation attempt: User {current_user.email} without users.manage "
                    f"attempted to update role/active status of {target_user.email}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Only users with 'users.manage' permission can update roles or active status",
                )

        if request.role_id is not None:
            role = await self.role_crud.get_by_id(request.role_id)
            if not role:
                logger.warning(f"User update failed: Target role ID {request.role_id} does not exist")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assigned role ID '{request.role_id}' does not exist",
                )

        update_fields = {}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.is_active is not None:
            update_fields["is_active"] = request.is_active
        if request.role_id is not None:
            update_fields["role_id"] = request.role_id

        if not update_fields:
            return UserResponse(
                id=target_user.id,
                name=target_user.name,
                email=target_user.email,
                role_id=target_user.role_id,
                is_active=target_user.is_active,
                created_at=target_user.created_at,
                updated_at=target_user.updated_at,
            )

        updated_user = await self.user_crud.update_user(target_user_id, update_fields)
        return UserResponse(
            id=updated_user.id,
            name=updated_user.name,
            email=updated_user.email,
            role_id=updated_user.role_id,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
        )
