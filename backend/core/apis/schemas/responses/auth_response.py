from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Response schema returning JWT authentication credentials.
    Contains the bearer access token string and token type header value.
    """

    access_token: str = Field(..., description="Encoded JWT access token string")
    token_type: str = Field(default="bearer", description="Token authentication header type")
