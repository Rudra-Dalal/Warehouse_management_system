import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Panel } from "@/components/whitfield/primitives";
import { FULFILLMENT_STAGES, orders, type Order, type Stage } from "@/lib/wms-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/fulfillment")({
  head: () => ({
    meta: [
      { title: "Fulfillment — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Track every order through confirmed, reserved, picking, packed and shipped with SLA pressure surfaced first.",
      },
      { property: "og:title", content: "Fulfillment — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "The pick-pack-ship pipeline, stage by stage, across Reno and Columbus.",
      },
    ],
  }),
  component: FulfillmentPage,
});

const stageTone = (s: Stage) =>
  s === "SHIPPED" ? "ok" : s === "PACKED" ? "info" : s === "PICKING" ? "signal" : "neutral";

function FulfillmentPage() {
  const [selectedId, setSelectedId] = useState<string>(orders[0]!.id);
  const selected = orders.find((o) => o.id === selectedId)!;

  const counts = FULFILLMENT_STAGES.map((s) => ({
    stage: s,
    count: orders.filter((o) => o.stage === s).length,
  }));

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Fulfillment"
        description="Orders progress through five states. Everything approaching SLA rises to the top."
        actions={
          <>
            <Button>Print pick lists</Button>
            <Button variant="primary">Start wave</Button>
          </>
        }
      />

      {/* Pipeline */}
      <div className="panel overflow-x-auto">
        <div className="flex min-w-[720px] divide-x divide-border">
          {counts.map(({ stage, count }) => {
            const active = selected.stage === stage;
            const passed =
              FULFILLMENT_STAGES.indexOf(stage) < FULFILLMENT_STAGES.indexOf(selected.stage);
            return (
              <div key={stage} className="relative flex-1 px-4 py-5">
                <div
                  className={cn(
                    "absolute inset-x-0 top-0 h-[2px] transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]",
                    active ? "bg-signal" : passed ? "bg-foreground/30" : "bg-transparent",
                  )}
                />
                <p
                  className={cn(
                    "numeric text-[11px] tracking-[0.16em] uppercase transition-colors",
                    active ? "text-signal" : "text-muted-foreground",
                  )}
                >
                  {stage}
                </p>
                <div
                  className={cn(
                    "numeric mt-3 text-3xl leading-none font-semibold transition-colors",
                    active ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {count}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">orders</p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Panel title="Queue" meta={`${orders.length} orders`}>
          <ul className="divide-y divide-border">
            {orders.map((o) => (
              <li key={o.id}>
                <button
                  onClick={() => setSelectedId(o.id)}
                  className={cn(
                    "flex w-full items-center gap-4 px-4 py-3.5 text-left transition-colors",
                    o.id === selectedId ? "bg-surface-2" : "hover:bg-surface-2/60",
                  )}
                >
                  <span
                    className={cn(
                      "h-8 w-[2px] rounded-full transition-colors",
                      o.id === selectedId ? "bg-signal" : "bg-transparent",
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="numeric block text-sm font-medium">{o.id}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {o.seller} · {o.lines} lines · {o.units} units · {o.warehouse}
                    </span>
                  </span>
                  <span
                    className={cn(
                      "numeric text-xs",
                      o.slaHours > 0 && o.slaHours <= 2
                        ? "text-danger"
                        : o.slaHours <= 4
                          ? "text-warn"
                          : "text-muted-foreground",
                    )}
                  >
                    {o.slaHours === 0 ? "—" : `${o.slaHours}h`}
                  </span>
                  <StatusPill tone={stageTone(o.stage)}>{o.stage}</StatusPill>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        <OrderDetail order={selected} />
      </div>
    </AppShell>
  );
}

function OrderDetail({ order }: { order: Order }) {
  const idx = FULFILLMENT_STAGES.indexOf(order.stage);
  const next = FULFILLMENT_STAGES[idx + 1];

  return (
    <section key={order.id} className="anim-rise panel h-fit overflow-hidden">
      <div className="border-b border-border px-5 py-4">
        <p className="eyebrow">Order</p>
        <h2 className="numeric mt-2 text-xl font-semibold tracking-tight">{order.id}</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {order.seller} · placed {order.placed} · {order.destination}
        </p>
      </div>

      <ol className="px-5 py-5">
        {FULFILLMENT_STAGES.map((s, i) => {
          const done = i < idx;
          const active = i === idx;
          return (
            <li key={s} className="relative flex gap-3.5 pb-5 last:pb-0">
              {i < FULFILLMENT_STAGES.length - 1 ? (
                <span
                  className={cn(
                    "absolute top-3 left-[5px] h-full w-px transition-colors duration-500",
                    done ? "bg-foreground/30" : "bg-border",
                  )}
                />
              ) : null}
              <span
                className={cn(
                  "relative mt-1 size-2.5 shrink-0 rounded-full border transition-all duration-400 ease-[cubic-bezier(0.22,1,0.36,1)]",
                  active
                    ? "scale-125 border-signal bg-signal"
                    : done
                      ? "border-foreground/40 bg-foreground/40"
                      : "border-border-strong bg-surface",
                )}
              />
              <span className="min-w-0">
                <span
                  className={cn(
                    "numeric block text-xs tracking-[0.14em] uppercase transition-colors",
                    active
                      ? "font-semibold text-foreground"
                      : done
                        ? "text-muted-foreground"
                        : "text-muted-foreground/60",
                  )}
                >
                  {s}
                </span>
                {active ? (
                  <span className="anim-fade mt-1 block text-xs text-muted-foreground">
                    In progress · {order.units} units across {order.lines} lines
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="grid grid-cols-3 divide-x divide-border border-t border-border">
        {[
          [String(order.units), "units"],
          [String(order.lines), "lines"],
          [order.slaHours === 0 ? "met" : `${order.slaHours}h`, "sla"],
        ].map(([v, l]) => (
          <div key={l} className="px-4 py-4">
            <div className="numeric text-lg leading-none font-semibold">{v}</div>
            <div className="mt-1.5 text-[11px] tracking-wider text-muted-foreground uppercase">
              {l}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 border-t border-border px-5 py-4">
        <Button variant="primary" disabled={!next}>
          {next ? `Advance to ${next}` : "Completed"}
        </Button>
        <Button variant="ghost">Open order</Button>
      </div>
    </section>
  );
}
