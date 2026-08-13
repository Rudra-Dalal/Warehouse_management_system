/**
 * Speech-to-Text (STT) Provider Interface.
 * Pluggable abstraction supporting Browser Web Speech API or external STT services.
 */

export type STTState = "idle" | "listening" | "processing" | "success" | "error" | "cancelled";

export interface STTResult {
  transcript: string;
  confidence: number;
}

export type STTStateCallback = (state: STTState) => void;
export type STTResultCallback = (result: STTResult) => void;
export type STTErrorCallback = (error: string) => void;

export interface SpeechToTextProvider {
  isSupported(): boolean;
  start(): Promise<void>;
  stop(): Promise<string>;
  cancel(): void;
  getState(): STTState;
  onStateChange(cb: STTStateCallback): () => void;
  onTranscript(cb: STTResultCallback): () => void;
  onError(cb: STTErrorCallback): () => void;
}
