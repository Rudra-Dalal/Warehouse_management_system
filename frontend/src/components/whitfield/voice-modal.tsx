import React, { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Mic, MicOff, AlertCircle, CheckCircle2, XCircle, X, ShieldAlert } from "lucide-react";
import { voiceController, VoiceHistoryEntry } from "@/voice/voice-controller";
import { STTState } from "@/voice/stt/provider";
import { useAuth } from "@/auth/auth-context";
import { Button } from "./primitives";

export function VoiceModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [sttState, setSttState] = useState<STTState>("idle");
  const [transcript, setTranscript] = useState("");
  const [pendingConfirmation, setPendingConfirmation] = useState<any | null>(null);
  const [history, setHistory] = useState<VoiceHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    voiceController.setNavigationHandler((path) => {
      onOpenChange(false);
      navigate({ to: path as any });
    });

    const unsubscribe = voiceController.subscribe((state) => {
      setSttState(state.sttState);
      setTranscript(state.transcript);
      setPendingConfirmation(state.pendingConfirmation);
      setHistory(state.history);
      setError(state.error);
    });

    return () => unsubscribe();
  }, [navigate, onOpenChange]);

  if (!open) return null;

  const handleMicClick = async () => {
    if (sttState === "listening") {
      await voiceController.stopAndProcess(user);
    } else {
      try {
        await voiceController.startListening();
      } catch (err: any) {
        setError(err.message || "Failed to access microphone.");
      }
    }
  };

  const handleConfirmMutation = async () => {
    await voiceController.confirmPendingCommand();
  };

  const handleCancelMutation = () => {
    voiceController.cancelPendingCommand();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[10vh]">
      {/* Backdrop */}
      <div
        className="anim-fade absolute inset-0 bg-foreground/40 backdrop-blur-xs"
        onClick={() => onOpenChange(false)}
      />

      {/* Modal Card */}
      <div className="anim-pop relative w-full max-w-lg overflow-hidden rounded-xl border border-border bg-popover shadow-2xl space-y-4 p-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-signal">
              <Mic className="size-4 text-signal-foreground" />
            </span>
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                WMS Voice Controller
              </h2>
              <p className="text-[11px] text-muted-foreground">
                STT Command Interface · Natural Language
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              voiceController.cancel();
              onOpenChange(false);
            }}
            className="text-muted-foreground hover:text-foreground p-1 transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Mic Visualizer & Trigger */}
        <div className="flex flex-col items-center justify-center py-6 space-y-4 bg-surface-2/40 rounded-lg border border-border">
          <button
            onClick={handleMicClick}
            className={`relative grid size-16 place-items-center rounded-full transition-all duration-300 ${
              sttState === "listening"
                ? "bg-signal text-signal-foreground scale-110 shadow-lg shadow-signal/30"
                : "bg-primary text-primary-foreground hover:scale-105"
            }`}
          >
            {sttState === "listening" ? (
              <span className="absolute inset-0 rounded-full bg-signal opacity-30 animate-ping" />
            ) : null}
            <Mic className="size-7 relative z-10" />
          </button>

          <div className="text-center">
            <span className="numeric text-xs font-semibold uppercase tracking-wider text-foreground">
              {sttState === "listening"
                ? "● Listening to Voice..."
                : sttState === "processing"
                  ? "Processing Intent..."
                  : "Click Mic to Speak"}
            </span>
            <p className="mt-1 text-xs text-muted-foreground">
              Try: "Show inventory for SKU 1048" or "What orders are ready to pack?"
            </p>
          </div>
        </div>

        {/* Live Transcript Preview */}
        {transcript ? (
          <div className="rounded-md border border-border bg-surface p-3">
            <p className="numeric text-[10px] font-medium tracking-wider uppercase text-muted-foreground">
              Recognized Transcript
            </p>
            <p className="mt-1 text-sm font-mono text-foreground">"{transcript}"</p>
          </div>
        ) : null}

        {/* Error Feedback */}
        {error ? (
          <div className="flex items-center gap-2.5 rounded-lg border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
            <AlertCircle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Pending Mutation Confirmation Dialog */}
        {pendingConfirmation ? (
          <div className="rounded-xl border border-signal/40 bg-signal/5 p-4 space-y-3">
            <div className="flex items-center gap-2 text-signal">
              <ShieldAlert className="size-5 shrink-0" />
              <h3 className="text-sm font-semibold">Confirmation Required</h3>
            </div>
            <p className="text-xs text-foreground font-mono">
              Action: <span className="font-semibold uppercase">{pendingConfirmation.intent}</span>
            </p>
            <p className="text-xs text-muted-foreground">
              Transcript: "{pendingConfirmation.originalTranscript}"
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={handleCancelMutation}>
                Cancel
              </Button>
              <Button size="sm" variant="primary" onClick={handleConfirmMutation}>
                Confirm Execution
              </Button>
            </div>
          </div>
        ) : null}

        {/* Recent Voice Command History */}
        {history.length > 0 ? (
          <div className="space-y-2 pt-2 border-t border-border">
            <p className="numeric text-[10px] font-medium tracking-wider uppercase text-muted-foreground">
              Shift Voice History
            </p>
            <ul className="divide-y divide-border max-h-36 overflow-y-auto">
              {history.map((item) => (
                <li key={item.id} className="flex items-center justify-between py-2 text-xs">
                  <span className="min-w-0 flex-1 truncate pr-2 font-mono">
                    "{item.transcript}"
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="numeric text-[10px] text-muted-foreground">
                      {item.timestamp}
                    </span>
                    {item.status === "completed" ? (
                      <CheckCircle2 className="size-3.5 text-ok" />
                    ) : item.status === "denied" ? (
                      <ShieldAlert className="size-3.5 text-danger" />
                    ) : (
                      <XCircle className="size-3.5 text-muted-foreground" />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
