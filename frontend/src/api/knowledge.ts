/**
 * RAG Knowledge Center API Client.
 * Communicates with backend /v1/knowledge.
 */
import { api } from "./client";
import { RAGSourceCitation } from "./ai";

export interface KnowledgeStatusResponse {
  indexed_chunks: number;
  is_indexed: boolean;
  handbook_pdf_path: string;
  handbook_pdf_exists: boolean;
  similarity_threshold: number;
}

export interface KnowledgeSearchPayload {
  query: string;
}

export interface KnowledgeSearchResponse {
  query: string;
  answer?: string | null;
  sources: RAGSourceCitation[];
  confidence: number;
  message?: string | null;
}

export async function getKnowledgeStatusApi(): Promise<KnowledgeStatusResponse> {
  return api.get<KnowledgeStatusResponse>("/v1/knowledge/status");
}

export async function searchKnowledgeApi(
  payload: KnowledgeSearchPayload
): Promise<KnowledgeSearchResponse> {
  return api.post<KnowledgeSearchResponse>("/v1/knowledge/search", payload);
}

export async function triggerKnowledgeIngestApi(): Promise<{ status: string; stats: any }> {
  return api.post<{ status: string; stats: any }>("/v1/knowledge/ingest");
}
