import os
from pydantic_settings import BaseSettings


class RAGSettings(BaseSettings):
    """Configuration for text-based RAG Knowledge Center."""

    KNOWLEDGE_PDF_PATH: str = os.path.join(
        "core", "database", "knowledge", "wms_operations_and_knowledge_handbook.pdf"
    )
    EMBEDDING_PROVIDER: str = os.getenv("RAG_EMBEDDING_PROVIDER", "local")  # 'local', 'openai', or 'mock'
    LLM_PROVIDER: str = os.getenv("RAG_LLM_PROVIDER", "local")  # 'local', 'openai', or 'mock'
    EMBEDDING_DIMENSION: int = 384
    TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.45
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")


rag_settings = RAGSettings()
