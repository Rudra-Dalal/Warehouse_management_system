import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  BookOpen,
  Send,
  Database,
  RefreshCw,
  FileText,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Copy,
  Check,
  Trash2,
} from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Input } from "@/components/whitfield/primitives";
import { askAiApi, AIAskResponse } from "@/api/ai";
import { getKnowledgeStatusApi, triggerKnowledgeIngestApi } from "@/api/knowledge";
import { useAuth } from "@/auth/auth-context";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/knowledge")({
  head: () => ({
    meta: [
      { title: "Knowledge Center & AI Assistant — Whitfield Fulfillment" },
      {
        name: "description",
        content: "Grounded WMS operational assistant with live tools and handbook vector RAG.",
      },
    ],
  }),
  component: KnowledgePage,
});

const QUICK_PROMPTS = [
  "What is the receiving protocol for damaged items?",
  "What are the inventory quarantine and discrepancy rules?",
  "Give me an inventory overview for Reno hub",
  "How many customer orders are currently active?",
];

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={idx}
          className="rounded bg-surface px-1.5 py-0.5 font-mono text-[11px] text-signal border border-border"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function FormattedAnswer({ text }: { text: string }) {
  const paragraphs = text.split("\n\n");

  return (
    <div className="space-y-3 text-sm leading-relaxed text-foreground/95">
      {paragraphs.map((p, pIdx) => {
        const lines = p.split("\n").filter((l) => l.trim().length > 0);
        const isList = lines.length > 0 && lines.every((l) => /^\d+\.\s+|^[-*]\s+/.test(l.trim()));

        if (isList) {
          return (
            <ul key={pIdx} className="space-y-2 my-2">
              {lines.map((line, lIdx) => {
                const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
                const bulletMatch = line.trim().match(/^[-*]\s+(.*)/);

                if (numMatch) {
                  return (
                    <li key={lIdx} className="flex items-start gap-2.5">
                      <span className="shrink-0 flex size-5 items-center justify-center rounded-full bg-signal/15 text-signal font-mono text-[11px] font-semibold mt-0.5">
                        {numMatch[1]}
                      </span>
                      <span className="flex-1 text-sm leading-normal">
                        {renderInlineMarkdown(numMatch[2])}
                      </span>
                    </li>
                  );
                }
                if (bulletMatch) {
                  return (
                    <li key={lIdx} className="flex items-start gap-2.5">
                      <span className="shrink-0 size-1.5 rounded-full bg-signal mt-2" />
                      <span className="flex-1 text-sm leading-normal">
                        {renderInlineMarkdown(bulletMatch[1])}
                      </span>
                    </li>
                  );
                }
                return <li key={lIdx}>{renderInlineMarkdown(line)}</li>;
              })}
            </ul>
          );
        }

        return (
          <p key={pIdx}>
            {lines.map((l, lIdx) => (
              <span key={lIdx} className={cn(lIdx > 0 && "block mt-1")}>
                {renderInlineMarkdown(l)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function CopyAnswerButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("Answer copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy text");
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer px-2 py-1 rounded hover:bg-surface"
      title="Copy answer"
    >
      {copied ? <Check className="size-3.5 text-ok" /> : <Copy className="size-3.5" />}
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

function KnowledgePage() {
  const queryClient = useQueryClient();
  const { activeWarehouse, user, hasPermission } = useAuth();
  const canIngest = hasPermission("user:write") || user?.role === "ADMIN";

  const [query, setQuery] = useState("");
  const [history, setHistory] = useState<
    Array<{
      query: string;
      response: AIAskResponse;
      timestamp: Date;
    }>
  >([]);

  // Knowledge vector store status query
  const { data: statusData, isLoading: isStatusLoading } = useQuery({
    queryKey: ["knowledge-status"],
    queryFn: getKnowledgeStatusApi,
  });

  // AI Ask mutation
  const askMutation = useMutation({
    mutationFn: askAiApi,
    onSuccess: (data, variables) => {
      setHistory((prev) => [
        { query: variables.query, response: data, timestamp: new Date() },
        ...prev,
      ]);
      setQuery("");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to query AI Assistant.");
    },
  });

  // Ingest handbook mutation
  const ingestMutation = useMutation({
    mutationFn: triggerKnowledgeIngestApi,
    onSuccess: (res) => {
      toast.success(
        `Handbook ingested: ${res.stats?.inserted ?? 0} chunks added (${res.stats?.pages ?? 0} pages).`,
      );
      queryClient.invalidateQueries({ queryKey: ["knowledge-status"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Ingestion failed.");
    },
  });

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = query.trim();
    if (!clean) return;
    askMutation.mutate({
      query: clean,
      warehouse_code: activeWarehouse || undefined,
    });
  };

  const handleQuickPrompt = (promptText: string) => {
    setQuery(promptText);
    askMutation.mutate({
      query: promptText,
      warehouse_code: activeWarehouse || undefined,
    });
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Intelligence & SOPs"
        title="Knowledge Center"
        description="Grounded AI assistant bridging live WMS database state with official warehouse operating procedures."
        actions={
          canIngest ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={ingestMutation.isPending}
              onClick={() => ingestMutation.mutate()}
            >
              <RefreshCw
                className={cn("size-3.5 mr-1.5", ingestMutation.isPending && "animate-spin")}
              />
              {ingestMutation.isPending ? "Indexing PDF..." : "Re-index Handbook"}
            </Button>
          ) : undefined
        }
      />

      {/* Top Stats Banner */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-4 flex items-center gap-3.5">
          <div className="grid size-9 place-items-center rounded-lg bg-signal/10 text-signal">
            <Database className="size-4" />
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              Vector Index
            </p>
            <p className="numeric text-lg font-semibold">
              {isStatusLoading ? "..." : `${statusData?.indexed_chunks ?? 0} Chunks`}
            </p>
          </div>
        </div>

        <div className="panel p-4 flex items-center gap-3.5">
          <div className="grid size-9 place-items-center rounded-lg bg-ok/10 text-ok">
            <Cpu className="size-4" />
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              Active Context
            </p>
            <p className="text-sm font-semibold tracking-wide">
              {activeWarehouse ? `${activeWarehouse} Hub` : "All Hubs (Admin)"}
            </p>
          </div>
        </div>

        <div className="panel p-4 flex items-center gap-3.5">
          <div className="grid size-9 place-items-center rounded-lg bg-surface-2 text-foreground">
            <BookOpen className="size-4" />
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              Handbook Status
            </p>
            <p className="text-sm font-semibold">
              {statusData?.is_indexed ? (
                <span className="text-ok flex items-center gap-1">
                  <CheckCircle2 className="size-3.5" /> Synced & Ready
                </span>
              ) : (
                <span className="text-danger flex items-center gap-1">
                  <AlertCircle className="size-3.5" /> Not Indexed
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Query Console */}
      <div className="panel overflow-hidden border-border-strong/60 shadow-xs">
        <div className="border-b border-border bg-surface-2/40 px-5 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-signal" />
            <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Ask WMS Operational Assistant
            </span>
          </div>
          <span className="text-[11px] font-mono text-muted-foreground">
            Authoritative RBAC · Grounded Tool Calls · RAG Vector Search
          </span>
        </div>

        <div className="p-5 sm:p-6 space-y-4">
          <form onSubmit={handleAsk} className="flex gap-2.5">
            <div className="relative flex-1">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask about live inventory levels, active orders, receiving SOPs, or warehouse policies..."
                className="pr-10 h-11 text-sm bg-background"
                disabled={askMutation.isPending}
                autoFocus
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-muted-foreground">
                ↵
              </span>
            </div>
            <Button
              type="submit"
              variant="primary"
              disabled={askMutation.isPending || !query.trim()}
              className="h-11 px-5"
            >
              {askMutation.isPending ? (
                <RefreshCw className="size-4 animate-spin" />
              ) : (
                <>
                  <Send className="size-4 mr-1.5" /> Ask
                </>
              )}
            </Button>
          </form>

          {/* Quick Prompts */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-[11px] font-mono text-muted-foreground mr-1">Suggested:</span>
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => handleQuickPrompt(prompt)}
                disabled={askMutation.isPending}
                className="rounded-full border border-border bg-surface-2/60 px-3 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-signal/40 hover:bg-surface-2 transition-colors cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Answers & History Feed */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Activity & History
          </h2>
          {history.length > 0 && (
            <button
              type="button"
              onClick={() => setHistory([])}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-danger transition-colors cursor-pointer"
            >
              <Trash2 className="size-3.5" />
              <span>Clear History</span>
            </button>
          )}
        </div>

        {askMutation.isPending && (
          <div className="anim-rise panel p-6 border-signal/30 bg-signal/5">
            <div className="flex items-center gap-3">
              <div className="size-4 rounded-full border-2 border-signal border-t-transparent animate-spin" />
              <p className="text-sm font-mono text-signal">
                Executing intent routing & authoritative live tool execution...
              </p>
            </div>
          </div>
        )}

        {history.length === 0 && !askMutation.isPending && (
          <div className="panel flex flex-col items-center justify-center p-12 text-center">
            <div className="grid size-12 place-items-center rounded-2xl bg-surface-2 text-muted-foreground mb-3">
              <Sparkles className="size-6" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">
              Operational Intelligence Ready
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm mt-1">
              Ask questions to query real-time warehouse data or extract standard procedures from
              the official WMS handbook.
            </p>
          </div>
        )}

        {history.map((item, idx) => (
          <div key={idx} className="anim-rise panel overflow-hidden space-y-4 p-5 sm:p-6">
            {/* User Prompt Row */}
            <div className="flex items-start justify-between gap-4 border-b border-border/80 pb-3.5">
              <div className="flex items-center gap-2.5">
                <div className="grid size-6 place-items-center rounded-full bg-surface-2 text-xs font-semibold text-foreground">
                  Q
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{item.query}</p>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {item.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <StatusPill
                  tone={
                    item.response.source === "LIVE_DATA"
                      ? "ok"
                      : item.response.source === "HANDBOOK"
                        ? "signal"
                        : item.response.source === "COMBINED"
                          ? "warn"
                          : "neutral"
                  }
                >
                  {item.response.source === "LIVE_DATA"
                    ? "Live WMS Tool"
                    : item.response.source === "HANDBOOK"
                      ? "Handbook RAG"
                      : item.response.source === "COMBINED"
                        ? "Live + SOPs"
                        : "System"}
                </StatusPill>
                {item.response.warehouse_context && (
                  <span className="numeric text-[11px] text-muted-foreground border border-border px-2 py-0.5 rounded">
                    {item.response.warehouse_context}
                  </span>
                )}
              </div>
            </div>

            {/* Direct Grounded Answer Content */}
            <div className="rounded-lg bg-surface-2/30 border border-border/60 p-4 sm:p-5 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-signal">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-3.5" />
                  <span>Direct Answer</span>
                </div>
                <CopyAnswerButton text={item.response.response} />
              </div>
              <FormattedAnswer text={item.response.response} />
            </div>

            {/* Source Citations Panel (if handbook RAG was used) */}
            {item.response.sources && item.response.sources.length > 0 && (
              <div className="pt-2 space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <FileText className="size-3.5 text-signal" /> Supporting Handbook Citations (
                  {item.response.sources.length})
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {item.response.sources.map((src, sIdx) => (
                    <div
                      key={sIdx}
                      className="rounded-lg border border-border bg-surface-2/70 p-3.5 text-xs space-y-2 hover:border-signal/40 transition-colors"
                    >
                      <div className="flex items-center justify-between text-muted-foreground font-mono text-[11px]">
                        <span className="font-semibold text-foreground truncate max-w-[180px]">
                          {src.source}
                        </span>
                        <span className="shrink-0 rounded bg-surface px-1.5 py-0.5 border border-border">
                          Page {src.page} · {Math.round(src.score * 100)}% match
                        </span>
                      </div>
                      <p className="text-muted-foreground text-[11px] leading-relaxed line-clamp-4 italic border-l-2 border-signal/40 pl-2">
                        "{src.excerpt}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
