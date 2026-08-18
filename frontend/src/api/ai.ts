/**
 * Operational AI Assistant API Client.
 * Communicates with backend /v1/ai/ask.
 */
import { api } from "./client";

export interface AIAskPayload {
  query: string;
  warehouse_code?: string | null | undefined;
}

export interface RAGSourceCitation {
  source: string;
  page: number;
  score: number;
  excerpt: string;
}

export interface AIAskResponse {
  response: string;
  source: "LIVE_DATA" | "HANDBOOK" | "COMBINED" | "ERROR";
  sources?: RAGSourceCitation[] | undefined;
  warehouse_context?: string | null | undefined;
}

export async function askAiApi(payload: AIAskPayload): Promise<AIAskResponse> {
  return api.post<AIAskResponse>("/v1/ai/ask", payload);
}
