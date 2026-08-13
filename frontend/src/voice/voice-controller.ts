/**
 * Voice Controller managing Speech-to-Text lifecycle, intent parsing,
 * RBAC authorization checks, confirmation dialog workflows, and execution.
 */

import { SpeechToTextProvider, STTState } from "./stt/provider";
import { BrowserSpeechToTextProvider } from "./stt/browser-provider";
import { parseVoiceCommand, VoiceCommand } from "./command-parser";
import { executeVoiceCommandApi, VoiceCommandApiResponse } from "@/api/voice";
import { hasPermission as checkPermission } from "@/auth/rbac";
import { User, Permission } from "@/types/wms";

export interface VoiceHistoryEntry {
  id: string;
  timestamp: string;
  transcript: string;
  intent: string;
  status: "completed" | "error" | "denied" | "confirmation_pending";
  message: string;
}

export type VoiceControllerListener = (state: {
  sttState: STTState;
  transcript: string;
  activeCommand: VoiceCommand | null;
  pendingConfirmation: VoiceCommand | null;
  history: VoiceHistoryEntry[];
  error: string | null;
}) => void;

export class VoiceController {
  private sttProvider: SpeechToTextProvider;
  private sttState: STTState = "idle";
  private transcript = "";
  private activeCommand: VoiceCommand | null = null;
  private pendingConfirmation: VoiceCommand | null = null;
  private history: VoiceHistoryEntry[] = [];
  private error: string | null = null;

  private listeners: Set<VoiceControllerListener> = new Set();
  private navigationHandler?: (path: string) => void;

  constructor(provider?: SpeechToTextProvider) {
    this.sttProvider = provider || new BrowserSpeechToTextProvider();

    this.sttProvider.onStateChange((s) => {
      this.sttState = s;
      this.notify();
    });

    this.sttProvider.onTranscript((res) => {
      this.transcript = res.transcript;
      this.notify();
    });

    this.sttProvider.onError((err) => {
      this.error = err;
      this.notify();
    });
  }

  public setNavigationHandler(handler: (path: string) => void) {
    this.navigationHandler = handler;
  }

  public isSupported(): boolean {
    return this.sttProvider.isSupported();
  }

  public async startListening(): Promise<void> {
    this.error = null;
    this.transcript = "";
    this.activeCommand = null;
    this.pendingConfirmation = null;
    await this.sttProvider.start();
  }

  public async stopAndProcess(currentUser: User | null): Promise<VoiceCommand | null> {
    const finalTranscript = await this.sttProvider.stop();
    const textToProcess = finalTranscript || this.transcript;

    if (!textToProcess.trim()) {
      this.error = "No speech detected.";
      this.notify();
      return null;
    }

    const command = parseVoiceCommand(textToProcess);
    this.activeCommand = command;

    if (command.clarificationNeeded) {
      this.addHistory(textToProcess, command.intent, "error", command.clarificationNeeded);
      this.error = command.clarificationNeeded;
      this.notify();
      return command;
    }

    // 1. Check RBAC permissions for mutating commands
    if (command.isMutating) {
      let requiredPerm: Permission = "inventory:adjust";
      if (command.intent === "reserve_inventory") requiredPerm = "inventory:reserve";

      if (!checkPermission(currentUser, requiredPerm)) {
        const msg = `Permission denied: You do not have permission to execute ${command.intent}.`;
        this.error = msg;
        this.addHistory(textToProcess, command.intent, "denied", msg);
        this.notify();
        return command;
      }

      // Mutating command requires confirmation
      this.pendingConfirmation = command;
      this.notify();
      return command;
    }

    // 2. Read-Only commands execute directly
    await this.executeCommand(command, false);
    return command;
  }

  public cancel(): void {
    this.sttProvider.cancel();
    this.transcript = "";
    this.activeCommand = null;
    this.pendingConfirmation = null;
    this.notify();
  }

  public async confirmPendingCommand(): Promise<void> {
    if (!this.pendingConfirmation) return;
    const cmd = this.pendingConfirmation;
    this.pendingConfirmation = null;
    await this.executeCommand(cmd, true);
  }

  public cancelPendingCommand(): void {
    if (this.pendingConfirmation) {
      this.addHistory(
        this.pendingConfirmation.originalTranscript,
        this.pendingConfirmation.intent,
        "error",
        "Command cancelled by user."
      );
    }
    this.pendingConfirmation = null;
    this.notify();
  }

  public subscribe(listener: VoiceControllerListener): () => void {
    this.listeners.add(listener);
    // Initial emit
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  public getState() {
    return {
      sttState: this.sttState,
      transcript: this.transcript,
      activeCommand: this.activeCommand,
      pendingConfirmation: this.pendingConfirmation,
      history: this.history,
      error: this.error,
    };
  }

  private async executeCommand(command: VoiceCommand, confirmed: boolean): Promise<void> {
    try {
      const response: VoiceCommandApiResponse = await executeVoiceCommandApi({
        transcript: command.originalTranscript,
        intent: command.intent,
        entities: command.entities,
        confirmed,
      });

      this.addHistory(
        command.originalTranscript,
        command.intent,
        response.status === "error" ? "error" : "completed",
        response.message
      );

      // Automatic route navigation for read lookup intents if navigation handler exists
      if (this.navigationHandler) {
        if (command.intent === "inventory_lookup") this.navigationHandler("/inventory");
        else if (command.intent === "product_lookup") this.navigationHandler("/products");
        else if (command.intent === "order_lookup") this.navigationHandler("/orders");
        else if (command.intent === "fulfillment_lookup") this.navigationHandler("/fulfillment");
        else if (command.intent === "audit_lookup") this.navigationHandler("/audit");
        else if (command.intent === "dashboard_lookup") this.navigationHandler("/");
      }

      this.notify();
    } catch (err: any) {
      const errMsg = err.message || "Voice command execution failed.";
      this.error = errMsg;
      this.addHistory(command.originalTranscript, command.intent, "error", errMsg);
      this.notify();
    }
  }

  private addHistory(
    transcript: string,
    intent: string,
    status: VoiceHistoryEntry["status"],
    message: string
  ) {
    const entry: VoiceHistoryEntry = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      transcript,
      intent,
      status,
      message,
    };
    this.history = [entry, ...this.history.slice(0, 9)];
  }

  private notify() {
    const state = this.getState();
    this.listeners.forEach((fn) => fn(state));
  }
}

// Global Singleton Instance
export const voiceController = new VoiceController();
