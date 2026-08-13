from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SellerCreateRequest(BaseModel):
    """Request schema for creating a new e-commerce seller account.
    Validates required seller code, name, and optional contact details.
    """

    code: str = Field(..., min_length=2, description="Unique seller code string")
    name: str = Field(..., description="Full seller business name")
    email: Optional[EmailStr] = Field(default=None, description="Contact email address")
    phone: Optional[str] = Field(default=None, description="Contact phone number")


class SellerUpdateRequest(BaseModel):
    """Request schema for updating an existing seller account details.
    Supports partial profile updates and active state toggle.
    """

    name: Optional[str] = Field(default=None, description="Updated seller business name")
    email: Optional[EmailStr] = Field(default=None, description="Updated contact email address")
    phone: Optional[str] = Field(default=None, description="Updated contact phone number")
    is_active: Optional[bool] = Field(default=None, description="Updated active status flag")
