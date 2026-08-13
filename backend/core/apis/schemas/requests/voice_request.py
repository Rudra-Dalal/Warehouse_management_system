from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VoiceCommandRequest(BaseModel):
    transcript: str = Field(..., description="Raw STT transcript string")
    intent: str = Field(..., description="Parsed intent name")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confirmed: bool = Field(default=False, description="Whether user explicitly confirmed a mutating action")
