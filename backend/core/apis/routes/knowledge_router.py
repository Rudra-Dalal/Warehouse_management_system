"""
Knowledge Router — Endpoints for handbook search and RAG ingestion status.
"""
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from commons.auth import get_current_user, require_permission
from commons.logger import get_logger
from core.models.user_model import UserModel
from core.rag.config import rag_settings
from core.rag.ingestion import ingest_pdf
from core.rag.retriever import RAGRetriever
from core.database.database import DatabaseManager

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge Center"])
retriever = RAGRetriever()


class KnowledgeSearchRequest(BaseModel):
    query: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    sources: list[Dict[str, Any]] = []
    confidence: float
    message: Optional[str] = None


@router.get("/status")
async def get_knowledge_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Returns the current ingestion status of the Knowledge Center vector store."""
    db = DatabaseManager.get_db()
    collection = db["rag_knowledge_chunks"]
    count = await collection.count_documents({})
    pdf_exists = os.path.exists(rag_settings.KNOWLEDGE_PDF_PATH)
    return {
        "indexed_chunks": count,
        "is_indexed": count > 0,
        "handbook_pdf_path": rag_settings.KNOWLEDGE_PDF_PATH,
        "handbook_pdf_exists": pdf_exists,
        "similarity_threshold": rag_settings.SIMILARITY_THRESHOLD,
    }


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Performs semantic vector search against the WMS SOP handbook chunks."""
    logger.info(f"Knowledge search requested by {current_user.email}: {request.query}")
    result = await retriever.search(request.query)
    return KnowledgeSearchResponse(
        query=request.query,
        answer=result.get("answer"),
        sources=result.get("sources", []),
        confidence=result.get("confidence", 0.0),
        message=result.get("message"),
    )


@router.post("/ingest", dependencies=[Depends(require_permission("user:write"))])
async def trigger_ingest(
    current_user: UserModel = Depends(get_current_user),
):
    """Triggers handbook PDF ingestion into MongoDB chunk vector store. Admin / Manager only."""
    logger.info(f"RAG Ingest triggered by {current_user.email}")
    if not os.path.exists(rag_settings.KNOWLEDGE_PDF_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handbook PDF not found at {rag_settings.KNOWLEDGE_PDF_PATH}",
        )
    stats = await ingest_pdf(rag_settings.KNOWLEDGE_PDF_PATH, "WMS Operations & Knowledge Handbook")
    return {"status": "success", "stats": stats}
