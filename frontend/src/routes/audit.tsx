import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Search, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, Input, EmptyState } from "@/components/whitfield/primitives";
import { getAuditLogsApi } from "@/api/audit";
import { AuditLog } from "@/types/wms";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/audit")({
  head: () => ({
    meta: [
      { title: "Audit Trail — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "An immutable, expandable timeline of every inventory, reservation, receiving and access change across the warehouse network.",
      },
    ],
  }),
  component: AuditPage,
});

const ENTITY_KINDS = [
  "ALL",
  "INVENTORY",
  "RESERVATION",
  "RECEIVING",
  "ORDER",
  "PRODUCT",
  "USER",
] as const;

function AuditPage() {
  const [kind, setKind] = useState<(typeof ENTITY_KINDS)[number]>("ALL");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  const {
    data: auditLogs = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["audit"],
    queryFn: () => getAuditLogsApi({ limit: 100 }),
  });

  const events = useMemo(() => {
    const q = query.trim().toLowerCase();
    return auditLogs.filter((log) => {
      const matchesKind = kind === "ALL" || log.entity_type.toUpperCase().includes(kind);
      const matchesQuery =
        !q ||
        log.action.toLowerCase().includes(q) ||
        log.entity_id.toLowerCase().includes(q) ||
        log.user_id.toLowerCase().includes(q) ||
        (log.warehouse_id || "").toLowerCase().includes(q);
      return matchesKind && matchesQuery;
    });
  }, [auditLogs, kind, query]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Audit Trail"
        description="Immutable shift activity log. Every mutation is attributed to a user, warehouse and prior/new state."
        actions={
          <Button variant="ghost" onClick={() => refetch()}>
            <RefreshCw className="mr-1.5 size-4" /> Refresh Logs
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search action, entity ID or user"
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface p-1">
          {ENTITY_KINDS.map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              className={cn(
                "rounded-sm px-2.5 py-1.5 text-xs font-medium uppercase transition-colors",
                kind === k
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching audit trail timeline...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load audit trail"}
            </p>
          </div>
        ) : events.length === 0 ? (
          <EmptyState
            title="No audit events found"
            description="Clear query or filters to view broader audit history."
          />
        ) : (
          <ol className="px-4 py-2 sm:px-6 sm:py-4">
            {events.map((log, i) => {
              const isOpen = openId === log.audit_id;
              const formattedTime = new Date(log.timestamp).toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });

              return (
                <li key={log.audit_id || i} className="relative flex gap-4 sm:gap-6">
                  <div className="numeric w-[68px] shrink-0 pt-4 text-right text-[11px] text-muted-foreground">
                    {formattedTime}
                  </div>

                  <div className="relative flex flex-col items-center">
                    <span className="mt-[19px] size-2 shrink-0 rounded-full bg-signal" />
                    {i < events.length - 1 ? <span className="w-px flex-1 bg-border" /> : null}
                  </div>

                  <div className="min-w-0 flex-1 border-b border-border py-3.5 last:border-0">
                    <button
                      onClick={() => setOpenId(isOpen ? null : log.audit_id)}
                      className="group flex w-full items-start justify-between gap-4 text-left"
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{log.action}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {log.entity_type}: {log.entity_id}
                        </span>
                        <span className="numeric mt-1.5 block text-[11px] tracking-wide text-muted-foreground uppercase">
                          {log.warehouse_id ? `${log.warehouse_id} HUB · ` : ""}
                          User: {log.user_id}
                        </span>
                      </span>
                      <ChevronDown
                        className={cn(
                          "mt-1 size-4 shrink-0 text-muted-foreground transition-transform duration-200",
                          isOpen && "rotate-180",
                        )}
                      />
                    </button>

                    <div
                      className={cn(
                        "grid transition-[grid-template-rows,opacity] duration-300",
                        isOpen ? "mt-3 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                      )}
                    >
                      <div className="overflow-hidden">
                        <div className="rounded-md border border-border bg-surface-2/60 px-4 py-3 space-y-3">
                          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
                            {[
                              ["Audit ID", log.audit_id],
                              ["Entity Type", log.entity_type],
                              ["Warehouse", log.warehouse_id || "GLOBAL"],
                              ["User ID", log.user_id],
                            ].map(([k, v]) => (
                              <div key={k}>
                                <dt className="numeric text-[10px] tracking-[0.14em] text-muted-foreground uppercase">
                                  {k}
                                </dt>
                                <dd className="numeric mt-1 text-xs truncate">{v}</dd>
                              </div>
                            ))}
                          </dl>

                          {log.previous_state || log.new_state ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs font-mono">
                              {log.previous_state ? (
                                <div className="rounded border border-border bg-background p-2">
                                  <span className="text-[10px] uppercase text-muted-foreground block mb-1">
                                    Previous State
                                  </span>
                                  <pre className="text-[11px] overflow-x-auto">
                                    {JSON.stringify(log.previous_state, null, 2)}
                                  </pre>
                                </div>
                              ) : null}

                              {log.new_state ? (
                                <div className="rounded border border-border bg-background p-2">
                                  <span className="text-[10px] uppercase text-muted-foreground block mb-1">
                                    New State
                                  </span>
                                  <pre className="text-[11px] overflow-x-auto">
                                    {JSON.stringify(log.new_state, null, 2)}
                                  </pre>
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </AppShell>
  );
}
