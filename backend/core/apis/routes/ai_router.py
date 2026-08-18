"""
AI Router — POST /v1/ai/ask
Accepts natural language queries and routes them to the AI Operational Assistant.
Backend authorization is authoritative; the LLM never decides permissions.
"""
from fastapi import APIRouter, Depends

from commons.auth import get_current_user
from commons.logger import get_logger
from core.models.user_model import UserModel
from core.services.ai_service import AIRequest, AIResponse, AIService

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/ai", tags=["AI Assistant"])
ai_service = AIService()


@router.post("/ask", response_model=AIResponse)
async def ask_ai(
    request: AIRequest,
    current_user: UserModel = Depends(get_current_user),
) -> AIResponse:
    """Processes a natural language WMS query using the Operational AI Assistant.
    Routes between live WMS tool calls and RAG Handbook search.
    Enforces standard JWT authentication. Warehouse scope is validated inside each tool call.

    Args:
        request (AIRequest): Query string and optional active warehouse context.
        current_user (UserModel): Authenticated user from JWT bearer token.

    Returns:
        AIResponse: Grounded AI response with source type and optional RAG citations.
    """
    logger.info(f"POST /v1/ai/ask from {current_user.email} (wh={request.warehouse_code})")
    return await ai_service.ask(request, current_user)
