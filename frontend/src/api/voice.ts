/**
 * Voice Command API Module.
 * Sends structured intents & transcripts to backend /v1/voice/command.
 */

import { api } from "./client";

export interface VoiceCommandPayload {
  transcript: string;
  intent: string;
  entities: Record<string, any>;
  confirmed?: boolean;
}

export interface VoiceCommandApiResponse {
  intent: string;
  status: "success" | "confirmation_required" | "clarification_required" | "error";
  message: string;
  data?: any;
  requires_confirmation: boolean;
}

export async function executeVoiceCommandApi(
  payload: VoiceCommandPayload,
): Promise<VoiceCommandApiResponse> {
  return api.post<VoiceCommandApiResponse>("/v1/voice/command", payload);
}
