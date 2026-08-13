from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Request schema for creating a new user account.
    Validates required name, email, password, and security role ID.
    """

    name: str = Field(..., description="Full user name")
    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., min_length=6, description="Plaintext password (minimum 6 characters)")
    role_id: str = Field(..., description="ObjectId string of assigned security Role")


class UserUpdateRequest(BaseModel):
    """Request schema for updating an existing user account.
    Supports partial profile updates, active state changes, and role assignment.
    """

    name: Optional[str] = Field(default=None, description="Updated full user name")
    is_active: Optional[bool] = Field(default=None, description="Updated active status flag")
    role_id: Optional[str] = Field(default=None, description="Updated role ObjectId string")
