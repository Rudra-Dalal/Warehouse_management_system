from typing import Callable, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from commons.logger import get_logger
from commons.security import decode_access_token
from core.cruds.permission_crud import PermissionCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel

logger = get_logger(__name__)

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> UserModel:
    """Extracts and validates JWT Bearer credentials to resolve the authenticated user.
    Raises HTTP 401 Unauthorized if token is missing, invalid, expired, or user is inactive.

    Args:
        credentials (HTTPAuthorizationCredentials): Extracted Authorization HTTP header.

    Returns:
        UserModel: The active authenticated user domain object.
    """
    logger.info("Executing auth.get_current_user dependency")
    if not credentials or not credentials.credentials:
        logger.warning("Missing authentication credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as error:
        logger.warning(f"Invalid JWT authentication token: {error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        logger.warning("JWT token missing subject claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_crud = UserCRUD()
    user = await user_crud.get_by_id(user_id)
    if not user:
        logger.warning(f"Authenticated user ID {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Disabled user attempt: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_permission(required_permission: str) -> Callable:
    """Factory creating a FastAPI dependency enforcing granular permission access.
    Raises HTTP 403 Forbidden if authenticated user's role lacks required permission.

    Args:
        required_permission (str): Permission string name required to execute endpoint.

    Returns:
        Callable: FastAPI async dependency function.
    """

    async def permission_dependency(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        logger.info(f"Executing require_permission dependency check for '{required_permission}'")
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role:
            logger.warning(f"User {current_user.email} has unresolvable role_id {current_user.role_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Assigned role does not exist",
            )

        permission_crud = PermissionCRUD()
        permissions = await permission_crud.get_by_ids(role.permission_ids)
        permission_names = [p.name for p in permissions]

        if required_permission not in permission_names:
            logger.warning(
                f"Permission denied for user {current_user.email}: "
                f"requires '{required_permission}', possesses {permission_names}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Permission '{required_permission}' required",
            )

        return current_user

    return permission_dependency


def require_role(required_role: str) -> Callable:
    """Factory creating a FastAPI dependency enforcing security role access.
    Raises HTTP 403 Forbidden if authenticated user does not belong to required role.

    Args:
        required_role (str): Security role name string required to execute endpoint.

    Returns:
        Callable: FastAPI async dependency function.
    """

    async def role_dependency(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        logger.info(f"Executing require_role dependency check for '{required_role}'")
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != required_role:
            logger.warning(
                f"Role check failed for user {current_user.email}: "
                f"requires '{required_role}', has '{role.name if role else None}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Role '{required_role}' required",
            )

        return current_user

    return role_dependency
