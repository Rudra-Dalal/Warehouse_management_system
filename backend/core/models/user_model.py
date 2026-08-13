from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    """Domain model representing an authenticated system user.
    Maintains identity, hashed credentials, role assignment, and active status.
    """

    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., description="Full user name")
    email: str = Field(..., description="Unique lowercased user email address")
    password_hash: str = Field(..., description="Securely hashed bcrypt password string")
    role_id: str = Field(..., description="ObjectId reference to assigned Role document")
    is_active: bool = Field(default=True, description="Active user status flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
