import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, Input, EmptyState } from "@/components/whitfield/primitives";
import { auditEvents, type AuditEvent } from "@/lib/wms-data";
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
      { property: "og:title", content: "Audit Trail — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Every change, attributed and timestamped. Read the warehouse day as a timeline.",
      },
    ],
  }),
  component: AuditPage,
});

const KINDS = ["all", "inventory", "reservation", "receiving", "order", "product", "auth"] as const;

const kindColor: Record<AuditEvent["kind"], string> = {
  inventory: "bg-signal",
  reservation: "bg-info",
  receiving: "bg-warn",
  order: "bg-ok",
  product: "bg-foreground/50",
  auth: "bg-danger",
};

function AuditPage() {
  const [kind, setKind] = useState<(typeof KINDS)[number]>("all");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(auditEvents[0]!.id);

  const events = useMemo(() => {
    const q = query.trim().toLowerCase();
    return auditEvents.filter(
      (e) =>
        (kind === "all" || e.kind === kind) &&
        (!q ||
          e.action.toLowerCase().includes(q) ||
          e.subject.toLowerCase().includes(q) ||
          e.user.toLowerCase().includes(q)),
    );
  }, [kind, query]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Audit Trail"
        description="Today · 13 August 2026. Every mutation is attributed to a user, warehouse and prior value."
        actions={<Button>Export log</Button>}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search action, subject or user"
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface p-1">
          {KINDS.map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              className={cn(
                "rounded-sm px-2.5 py-1.5 text-xs font-medium capitalize transition-colors",
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
        {events.length === 0 ? (
          <EmptyState
            title="No events in this slice"
            description="Widen the event type or clear the search to see the full shift history."
          />
        ) : (
          <ol className="px-4 py-2 sm:px-6 sm:py-4">
            {events.map((e, i) => {
              const open = openId === e.id;
              return (
                <li key={e.id} className="relative flex gap-4 sm:gap-6">
                  <div className="numeric w-[68px] shrink-0 pt-4 text-right text-[11px] text-muted-foreground">
                    {e.time}
                  </div>

                  <div className="relative flex flex-col items-center">
                    <span className={cn("mt-[19px] size-2 shrink-0 rounded-full", kindColor[e.kind])} />
                    {i < events.length - 1 ? (
                      <span className="w-px flex-1 bg-border" />
                    ) : null}
                  </div>

                  <div className="min-w-0 flex-1 border-b border-border py-3.5 last:border-0">
                    <button
                      onClick={() => setOpenId(open ? null : e.id)}
                      className="group flex w-full items-start justify-between gap-4 text-left"
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{e.action}</span>
                        <span className="block truncate text-sm text-muted-foreground">
                          {e.subject}
                        </span>
                        {e.from || e.to ? (
                          <span className="numeric mt-1.5 inline-flex items-center gap-2 text-xs">
                            {e.field ? (
                              <span className="text-muted-foreground">{e.field}</span>
                            ) : null}
                            {e.from ? (
                              <>
                                <span className="text-muted-foreground line-through">{e.from}</span>
                                <span className="text-muted-foreground">→</span>
                              </>
                            ) : null}
                            <span className="font-medium text-foreground">{e.to}</span>
                          </span>
                        ) : null}
                        <span className="numeric mt-1.5 block text-[11px] tracking-wide text-muted-foreground uppercase">
                          {e.warehouse ? `${e.warehouse} · ` : ""}
                          {e.user} · {e.role}
                        </span>
                      </span>
                      <ChevronDown
                        className={cn(
                          "mt-1 size-4 shrink-0 text-muted-foreground transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                          open && "rotate-180",
                        )}
                      />
                    </button>

                    <div
                      className={cn(
                        "grid transition-[grid-template-rows,opacity] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
                        open ? "mt-3 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                      )}
                    >
                      <div className="overflow-hidden">
                        <div className="rounded-md border border-border bg-surface-2/60 px-4 py-3">
                          <p className="text-sm text-muted-foreground">{e.detail}</p>
                          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
                            {[
                              ["Event", e.id],
                              ["Type", e.kind],
                              ["Warehouse", e.warehouse ?? "—"],
                              ["Actor", e.user],
                            ].map(([k, v]) => (
                              <div key={k}>
                                <dt className="numeric text-[10px] tracking-[0.14em] text-muted-foreground uppercase">
                                  {k}
                                </dt>
                                <dd className="numeric mt-1 text-xs">{v}</dd>
                              </div>
                            ))}
                          </dl>
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
