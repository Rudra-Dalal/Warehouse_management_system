"""
RAG Retriever — Semantic search over the warehouse knowledge handbook chunks.
Uses Gemini for query embedding, then performs cosine-similarity search against 
MongoDB-stored chunk embeddings. Falls back gracefully if no chunks are ingested.
"""
import math
from typing import List, Dict, Any, Optional

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.rag.config import rag_settings

logger = get_logger(__name__)

KNOWLEDGE_COLLECTION = "rag_knowledge_chunks"


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_query(query: str) -> Optional[List[float]]:
    """Embed a single query string using Google Gemini, or return None if unavailable."""
    try:
        from google import genai
        client = genai.Client()
        result = client.models.embed_content(
            model="gemini-embedding-exp-03-07",
            contents=[query],
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.warning(f"Embedding query via Gemini failed (fallback to keyword search): {e}")
        return None


class RAGRetriever:
    """
    Retrieves relevant knowledge handbook chunks for a given query.
    Performs in-process cosine similarity search over MongoDB-stored embeddings.
    
    Note: For Atlas deployments, this can be replaced with $vectorSearch aggregation
    pipeline for server-side ANN search at scale.
    """

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search the knowledge base for chunks relevant to the query.
        Returns the top-k chunks above the similarity threshold, with source metadata.
        """
        logger.info(f"RAG search: '{query}'")
        db = DatabaseManager.get_db()
        collection = db[KNOWLEDGE_COLLECTION]

        # Check if we have any knowledge chunks
        count = await collection.count_documents({})
        if count == 0:
            logger.warning("RAG knowledge base is empty — no chunks ingested yet.")
            return {
                "answer": None,
                "chunks": [],
                "sources": [],
                "confidence": 0.0,
                "message": "Knowledge base is empty. Please ingest the handbook PDF first.",
            }

        # Embed the query
        query_embedding = _embed_query(query)

        # Fetch all chunks (for small corpora this is fine; replace with $vectorSearch for Atlas)
        cursor = collection.find({}, {"content": 1, "source": 1, "page": 1, "embedding": 1})
        chunks = await cursor.to_list(length=None)

        # Score by cosine similarity or keyword relevance
        scored = []
        q_words = [w.lower() for w in query.split() if len(w) > 2]
        for chunk in chunks:
            if query_embedding and "embedding" in chunk and chunk["embedding"]:
                score = _cosine_similarity(query_embedding, chunk["embedding"])
            else:
                # Keyword fallback score
                content_lower = chunk.get("content", "").lower()
                matches = sum(1 for w in q_words if w in content_lower)
                score = min(0.95, (matches / max(1, len(q_words))) * 0.8 + 0.1) if matches > 0 else 0.0

            scored.append({
                "content": chunk["content"],
                "source": chunk.get("source", "WMS Handbook"),
                "page": chunk.get("page", 0),
                "score": score,
            })


        # Sort and filter by threshold
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_k = scored[:rag_settings.TOP_K]
        above_threshold = [c for c in top_k if c["score"] >= rag_settings.SIMILARITY_THRESHOLD]

        if not above_threshold:
            return {
                "answer": None,
                "chunks": [],
                "sources": [],
                "confidence": 0.0,
                "message": "No sufficiently relevant handbook sections found for this query.",
            }

        # Build source citations
        sources = []
        for c in above_threshold:
            clean_txt = (
                c["content"]
                .replace("\u2193", " -> ")
                .replace("\u2192", " -> ")
                .replace("\u2022", "*")
                .replace("\u2013", "-")
                .replace("\u2014", "-")
            )
            sources.append({
                "source": c["source"],
                "page": c["page"],
                "score": round(c["score"], 3),
                "excerpt": clean_txt[:300] + ("..." if len(clean_txt) > 300 else ""),
            })

        context = "\n\n---\n\n".join(
            f"[Source: {c['source']}, Page {c['page']}]\n{c['content']}"
            for c in above_threshold
        )

        return {
            "answer": context,
            "chunks": above_threshold,
            "sources": sources,
            "confidence": above_threshold[0]["score"] if above_threshold else 0.0,
        }
