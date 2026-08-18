import os
from pydantic_settings import BaseSettings


def _resolve_default_pdf_path() -> str:
    env_path = os.getenv("KNOWLEDGE_PDF_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    
    relative_candidate = os.path.join("core", "database", "knowledge", "Whitfield_WMS_Final_Operations_Handbook.pdf")
    if os.path.exists(relative_candidate):
        return relative_candidate
        
    abs_candidate = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "database", "knowledge", "Whitfield_WMS_Final_Operations_Handbook.pdf")
    )
    if os.path.exists(abs_candidate):
        return abs_candidate
        
    return env_path or relative_candidate


class RAGSettings(BaseSettings):
    """Configuration for text-based RAG Knowledge Center."""

    KNOWLEDGE_PDF_PATH: str = _resolve_default_pdf_path()
    EMBEDDING_PROVIDER: str = os.getenv("RAG_EMBEDDING_PROVIDER", "gemini")
    EMBEDDING_DIMENSION: int = 768
    TOP_K: int = 2
    MAX_CITATIONS: int = 2
    SIMILARITY_THRESHOLD: float = 0.52
    SCORE_DELTA_THRESHOLD: float = 0.12
    SAFE_UNKNOWN_FALLBACK: str = (
        "The WMS handbook does not provide enough information to answer this question."
    )


rag_settings = RAGSettings()
