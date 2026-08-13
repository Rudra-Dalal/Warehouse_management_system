from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    """Response schema exposing permission metadata.
    Provides permission ID, unique name, and capability description.
    """

    id: str = Field(..., description="Permission ObjectId string")
    name: str = Field(..., description="Unique permission name")
    description: str = Field(..., description="Permission description")


class RoleResponse(BaseModel):
    """Response schema exposing role metadata and assigned permission IDs.
    Provides role ID, name, description, and list of permission IDs.
    """

    id: str = Field(..., description="Role ObjectId string")
    name: str = Field(..., description="Security role name")
    description: str = Field(..., description="Role description")
    permission_ids: List[str] = Field(default_factory=list, description="Assigned permission IDs")


class UserResponse(BaseModel):
    """Response schema for public user entity details.
    Excludes sensitive credential data like password_hash.
    """

    id: str = Field(..., description="User ObjectId string")
    name: str = Field(..., description="Full user name")
    email: str = Field(..., description="User email address")
    role_id: str = Field(..., description="Assigned Role ObjectId string")
    is_active: bool = Field(..., description="Active user status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Account last updated timestamp")


class UserMeResponse(BaseModel):
    """Response schema for GET /v1/auth/me current user endpoint.
    Includes user details along with resolved role name and permission list.
    """

    id: str = Field(..., description="User ObjectId string")
    name: str = Field(..., description="Full user name")
    email: str = Field(..., description="User email address")
    role: Optional[str] = Field(default=None, description="Assigned security role name")
    permissions: List[str] = Field(default_factory=list, description="List of granted permission names")
    is_active: bool = Field(..., description="Active user status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Account last updated timestamp")
