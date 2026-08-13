from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VoiceCommandResponse(BaseModel):
    intent: str = Field(..., description="Processed intent name")
    status: str = Field(..., description="Status: success, confirmation_required, clarification_required, or error")
    message: str = Field(..., description="Natural language feedback message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Result payload")
    requires_confirmation: bool = Field(default=False, description="True if mutating command requires user confirmation")
