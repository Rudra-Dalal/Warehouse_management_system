/**
 * Browser Web Speech API Implementation of SpeechToTextProvider.
 */

import {
  SpeechToTextProvider,
  STTState,
  STTResult,
  STTStateCallback,
  STTResultCallback,
  STTErrorCallback,
} from "./provider";

export class BrowserSpeechToTextProvider implements SpeechToTextProvider {
  private recognition: any = null;
  private state: STTState = "idle";
  private currentTranscript = "";
  private currentConfidence = 1.0;

  private stateListeners: Set<STTStateCallback> = new Set();
  private resultListeners: Set<STTResultCallback> = new Set();
  private errorListeners: Set<STTErrorCallback> = new Set();

  constructor() {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = "en-US";

        this.recognition.onstart = () => {
          this.setState("listening");
        };

        this.recognition.onresult = (event: any) => {
          let interim = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const res = event.results[i];
            if (res.isFinal) {
              this.currentTranscript = res[0].transcript.trim();
              this.currentConfidence = res[0].confidence || 0.95;
            } else {
              interim += res[0].transcript;
            }
          }
          const activeText = this.currentTranscript || interim.trim();
          if (activeText) {
            this.notifyResult({ transcript: activeText, confidence: this.currentConfidence });
          }
        };

        this.recognition.onerror = (event: any) => {
          if (event.error === "no-speech") {
            this.notifyError("No speech detected. Please speak into your microphone.");
          } else if (event.error === "not-allowed") {
            this.notifyError("Microphone access blocked. Enable permissions in browser settings.");
          } else {
            this.notifyError(`Speech recognition error: ${event.error}`);
          }
          this.setState("error");
        };

        this.recognition.onend = () => {
          if (this.state === "listening") {
            this.setState(this.currentTranscript ? "success" : "idle");
          }
        };
      }
    }
  }

  public isSupported(): boolean {
    return this.recognition !== null;
  }

  public getState(): STTState {
    return this.state;
  }

  public async start(): Promise<void> {
    if (!this.isSupported()) {
      const msg = "Speech recognition is not supported in this browser environment.";
      this.notifyError(msg);
      this.setState("error");
      throw new Error(msg);
    }

    this.currentTranscript = "";
    this.setState("listening");

    try {
      this.recognition.start();
    } catch (err: any) {
      // If already started
      if (err.name !== "InvalidStateError") {
        this.notifyError(err.message || "Failed to start microphone.");
        this.setState("error");
      }
    }
  }

  public async stop(): Promise<string> {
    this.setState("processing");
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Recognition already stopped
      }
    }
    this.setState("success");
    return this.currentTranscript;
  }

  public cancel(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Recognition already aborted
      }
    }
    this.currentTranscript = "";
    this.setState("cancelled");
  }

  public onStateChange(cb: STTStateCallback): () => void {
    this.stateListeners.add(cb);
    return () => this.stateListeners.delete(cb);
  }

  public onTranscript(cb: STTResultCallback): () => void {
    this.resultListeners.add(cb);
    return () => this.resultListeners.delete(cb);
  }

  public onError(cb: STTErrorCallback): () => void {
    this.errorListeners.add(cb);
    return () => this.errorListeners.delete(cb);
  }

  private setState(newState: STTState) {
    this.state = newState;
    this.stateListeners.forEach((fn) => fn(newState));
  }

  private notifyResult(result: STTResult) {
    this.resultListeners.forEach((fn) => fn(result));
  }

  private notifyError(errMsg: string) {
    this.errorListeners.forEach((fn) => fn(errMsg));
  }
}
