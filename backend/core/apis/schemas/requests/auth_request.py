from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request schema for user authentication login endpoint.
    Validates user email address and plaintext password format.
    """

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Plaintext password string")
