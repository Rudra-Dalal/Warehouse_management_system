"""
RAG Retriever — Semantic search over the warehouse knowledge handbook chunks.
Uses Gemini embeddings for cosine similarity vector search with domain keyword scoring,
filtering out irrelevant/weak chunks, and synthesizing direct grounded answers via RAGAnswerGenerator.
"""
import math
import re
from typing import List, Dict, Any, Optional

from commons.logger import get_logger
from core.database.database import DatabaseManager
from core.rag.config import rag_settings
from core.rag.generator import RAGAnswerGenerator

logger = get_logger(__name__)

KNOWLEDGE_COLLECTION = "rag_knowledge_chunks"

STOPWORDS = {
    "what", "is", "the", "for", "are", "and", "can", "how", "do", "does",
    "with", "from", "that", "this", "tell", "give", "about", "your", "you",
    "our", "a", "an", "of", "in", "on", "at", "to", "by", "or", "as", "be",
    "was", "were", "it", "its", "i", "me", "my", "we", "us", "item", "items",
    "system", "please", "would", "should", "could", "there", "any", "where",
    "which", "when", "why", "who", "all", "some"
}

DOMAIN_BOOSTS = {
    "damaged": 2.5,
    "damage": 2.5,
    "quarantine": 2.5,
    "discrepancy": 2.5,
    "receiving": 2.0,
    "receive": 2.0,
    "adjust": 2.0,
    "adjustment": 2.0,
    "upc": 2.0,
    "barcode": 2.0,
    "scanner": 2.0,
    "wedge": 2.0,
    "read_only": 2.2,
    "readonly": 2.2,
    "fulfillment": 2.0,
    "audit": 2.0,
    "zeros": 1.8,
    "sop": 1.8,
    "policy": 1.5,
    "workflow": 1.5,
}


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
        logger.debug(f"Embedding query via Gemini failed (fallback to domain keyword scoring): {e}")
        return None


def _calculate_keyword_score(query: str, chunk_content: str) -> float:
    """Calculates weighted domain keyword match score excluding common stopwords."""
    content_lower = chunk_content.lower()
    raw_words = re.findall(r'[a-z0-9_\-]+', query.lower())
    meaningful_terms = [w.replace("-", "_") for w in raw_words if len(w) > 2 and w not in STOPWORDS]

    if not meaningful_terms:
        return 0.0

    total_weight = 0.0
    matched_weight = 0.0

    for term in meaningful_terms:
        weight = DOMAIN_BOOSTS.get(term, 1.0)
        total_weight += weight
        # Check direct or base word presence
        base_term = term.rstrip("s").rstrip("ing").rstrip("ed")
        if term in content_lower or (len(base_term) > 3 and base_term in content_lower):
            matched_weight += weight

    if matched_weight == 0.0 or total_weight == 0.0:
        return 0.0

    ratio = matched_weight / total_weight
    # Scale: High match ratio gives 0.75 - 0.95; partial match gives 0.50 - 0.70
    return min(0.95, round(0.40 + 0.55 * ratio, 3))


class RAGRetriever:
    """
    Retrieves relevant knowledge handbook chunks for a given query
    and coordinates with RAGAnswerGenerator to return concise grounded answers.
    """

    def __init__(self):
        self.generator = RAGAnswerGenerator()

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search the knowledge base for chunks relevant to the query.
        Returns synthesized direct answer and top-k chunks above the similarity threshold with citations.
        """
        logger.info(f"RAG search: '{query}'")
        db = DatabaseManager.get_db()
        collection = db[KNOWLEDGE_COLLECTION]

        # Check if we have any knowledge chunks
        count = await collection.count_documents({})
        if count == 0:
            logger.warning("RAG knowledge base is empty — no chunks ingested yet.")
            return {
                "answer": "Knowledge base is empty. Please ingest the handbook PDF first.",
                "chunks": [],
                "sources": [],
                "confidence": 0.0,
                "message": "Knowledge base is empty. Please ingest the handbook PDF first.",
            }

        # Embed the query if GenAI is available
        query_embedding = _embed_query(query)

        # Fetch all chunks
        cursor = collection.find({}, {"content": 1, "source": 1, "page": 1, "embedding": 1})
        chunks = await cursor.to_list(length=None)

        # Score chunks by cosine similarity or domain keyword score
        scored = []
        for chunk in chunks:
            chunk_embedding = chunk.get("embedding")
            if query_embedding and chunk_embedding and len(chunk_embedding) > 0:
                score = _cosine_similarity(query_embedding, chunk_embedding)
            else:
                score = _calculate_keyword_score(query, chunk.get("content", ""))

            # Avoid boosting generic introductory chunks when asking specific questions
            content_lower = chunk.get("content", "").lower()
            if "about the warehouse management system" in content_lower and not any(w in query.lower() for w in ["about", "what is this system", "overview"]):
                score = score * 0.4  # Penalize generic intro chunk for specific queries

            scored.append({
                "content": chunk["content"],
                "source": chunk.get("source", "wms_operations_and_knowledge_handbook.pdf"),
                "page": chunk.get("page", 1),
                "score": score,
            })

        # Sort and filter by threshold
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_k = scored[:rag_settings.TOP_K]
        above_threshold = [c for c in top_k if c["score"] >= rag_settings.SIMILARITY_THRESHOLD]

        if not above_threshold:
            logger.info(f"No chunks above similarity threshold {rag_settings.SIMILARITY_THRESHOLD} for query: {query}")
            return {
                "answer": rag_settings.SAFE_UNKNOWN_FALLBACK,
                "chunks": [],
                "sources": [],
                "confidence": 0.0,
                "message": "No sufficiently relevant handbook sections found for this query.",
            }

        # Generate direct, grounded answer from relevant chunks
        answer = await self.generator.generate_answer(query, above_threshold)

        # Build clean source citations
        sources = []
        for c in above_threshold:
            clean_txt = (
                c["content"]
                .replace("\u2193", " -> ")
                .replace("\u2192", " -> ")
                .replace("\u2022", "*")
                .replace("\u2013", "-")
                .replace("\u2014", "-")
                .strip()
            )
            clean_txt = re.sub(r'\s+', ' ', clean_txt)
            sources.append({
                "source": c.get("source", "wms_operations_and_knowledge_handbook.pdf"),
                "page": c.get("page", 1),
                "score": round(c["score"], 3),
                "excerpt": clean_txt[:280] + ("..." if len(clean_txt) > 280 else ""),
            })

        return {
            "answer": answer,
            "chunks": above_threshold,
            "sources": sources,
            "confidence": round(above_threshold[0]["score"], 3) if above_threshold else 0.0,
        }
