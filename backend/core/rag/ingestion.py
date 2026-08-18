"""
RAG Ingestion — PDF loading, chunking, and embedding for the Warehouse Knowledge Handbook.
Uses pypdf for PDF reading, Google Gemini for embeddings, and stores chunks in MongoDB
with cosine-similarity vector search (Atlas Vector Search if available, fallback to in-memory).
"""
import os
import hashlib
from typing import List, Dict, Any
from pypdf import PdfReader

from commons.logger import get_logger
from core.database.database import DatabaseManager

logger = get_logger(__name__)

KNOWLEDGE_COLLECTION = "rag_knowledge_chunks"


async def _get_collection():
    db = DatabaseManager.get_db()
    return db[KNOWLEDGE_COLLECTION]


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def _embed_text(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Google Gemini embedding model, or return empty lists if unavailable."""
    try:
        from google import genai
        client = genai.Client()
        embeddings = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=batch,
            )
            for emb in result.embeddings:
                embeddings.append(emb.values)
        return embeddings
    except Exception as e:
        logger.warning(f"Embedding batch via Gemini failed during ingestion (storing chunks without embeddings): {e}")
        return [[] for _ in texts]



async def ingest_pdf(pdf_path: str, source_name: str = None) -> Dict[str, Any]:
    """
    Load, chunk, embed, and persist a PDF into MongoDB.
    Returns ingestion statistics.
    Idempotent: chunks are identified by content hash, so re-ingestion is safe.
    """
    logger.info(f"Starting RAG ingestion for: {pdf_path}")

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"Handbook PDF not found at {pdf_path}")

    # Extract text per page
    reader = PdfReader(pdf_path)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append({"page": i + 1, "text": text})

    logger.info(f"Extracted text from {len(pages_text)} pages")

    # Chunk all pages
    all_chunks = []
    for page_info in pages_text:
        page_chunks = _chunk_text(page_info["text"])
        for chunk in page_chunks:
            content_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]
            all_chunks.append({
                "content": chunk,
                "source": source_name or os.path.basename(pdf_path),
                "page": page_info["page"],
                "content_hash": content_hash,
            })

    logger.info(f"Created {len(all_chunks)} chunks — generating embeddings...")

    # Generate embeddings
    texts = [c["content"] for c in all_chunks]
    embeddings = _embed_text(texts)

    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb

    # Upsert into MongoDB (idempotent by content_hash)
    collection = await _get_collection()
    inserted = 0
    skipped = 0
    for chunk in all_chunks:
        existing = await collection.find_one({"content_hash": chunk["content_hash"]})
        if existing:
            skipped += 1
        else:
            await collection.insert_one(chunk)
            inserted += 1

    logger.info(f"Ingestion complete: {inserted} inserted, {skipped} skipped")
    return {
        "pdf": pdf_path,
        "pages": len(pages_text),
        "total_chunks": len(all_chunks),
        "inserted": inserted,
        "skipped": skipped,
    }
