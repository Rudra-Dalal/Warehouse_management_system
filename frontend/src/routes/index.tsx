import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { Panel, StatusPill, Button } from "@/components/whitfield/primitives";
import { dashboard, orders, auditEvents } from "@/lib/wms-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Whitfield Fulfillment — Warehouse Operations Dashboard" },
      {
        name: "description",
        content:
          "Live warehouse operations across Reno and Columbus: available units, active orders, SLA risk and receiving discrepancies at a glance.",
      },
      { property: "og:title", content: "Whitfield Fulfillment — Operations Dashboard" },
      {
        property: "og:description",
        content:
          "Precision warehouse management: inventory, fulfillment, scanning and audit across Reno and Columbus.",
      },
    ],
  }),
  component: Dashboard,
});

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data);
  return (
    <div className="flex h-12 items-end gap-1">
      {data.map((v, i) => (
        <span
          key={i}
          className="flex-1 rounded-xs bg-foreground/15 transition-colors hover:bg-signal"
          style={{ height: `${(v / max) * 100}%` }}
        />
      ))}
    </div>
  );
}

function Dashboard() {
  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <AppShell>
      <section className="anim-rise border-b border-border pb-8">
        <p className="eyebrow">Warehouse operations · {today}</p>
        <h1 className="display-xl mt-3">{greeting()}</h1>

        <div className="mt-9 grid gap-8 border-t border-border pt-8 sm:grid-cols-3">
          <div>
            <div className="numeric display-lg">12,480</div>
            <p className="mt-2 text-sm text-muted-foreground">available units</p>
          </div>
          <div className="sm:border-l sm:border-border sm:pl-8">
            <div className="numeric display-lg">342</div>
            <p className="mt-2 text-sm text-muted-foreground">active orders</p>
          </div>
          <div className="sm:border-l sm:border-border sm:pl-8">
            <div className="numeric display-lg text-signal">18</div>
            <p className="mt-2 text-sm text-muted-foreground">need attention</p>
          </div>
        </div>
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel title="Attention" meta="Requires action this shift">
          <ul className="divide-y divide-border">
            {dashboard.attention.map((a, i) => (
              <li key={a.label}>
                <Link
                  to={a.to}
                  className="group flex items-center justify-between gap-4 px-4 py-4 transition-colors hover:bg-surface-2"
                >
                  <span className="flex items-center gap-3">
                    <span
                      className={
                        i === 0
                          ? "size-1.5 rounded-full bg-danger"
                          : i === 1
                            ? "size-1.5 rounded-full bg-warn"
                            : "size-1.5 rounded-full bg-info"
                      }
                    />
                    <span className="text-sm font-medium">{a.label}</span>
                  </span>
                  <ArrowUpRight className="size-4 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Warehouse" meta="Available · reserved">
          <div className="divide-y divide-border">
            {dashboard.warehouses.map((w) => (
              <div key={w.name} className="px-4 py-4">
                <div className="flex items-baseline justify-between">
                  <h3 className="numeric text-sm font-semibold tracking-[0.08em]">{w.name}</h3>
                  <span className="numeric text-xs text-muted-foreground">
                    {w.orders} open orders
                  </span>
                </div>
                <div className="mt-3 flex items-end gap-6">
                  <div>
                    <div className="numeric text-2xl leading-none font-semibold">
                      {w.available.toLocaleString()}
                    </div>
                    <div className="mt-1.5 text-xs text-muted-foreground">available</div>
                  </div>
                  <div>
                    <div className="numeric text-2xl leading-none font-semibold text-muted-foreground">
                      {w.reserved.toLocaleString()}
                    </div>
                    <div className="mt-1.5 text-xs text-muted-foreground">reserved</div>
                  </div>
                </div>
                <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-surface-2">
                  <div
                    className="h-full rounded-full bg-foreground/70 transition-[width] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]"
                    style={{ width: `${w.utilisation * 100}%` }}
                  />
                </div>
                <p className="numeric mt-2 text-[11px] tracking-wider text-muted-foreground uppercase">
                  {Math.round(w.utilisation * 100)}% capacity utilised
                </p>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Panel title="Throughput" meta="Units shipped · last 12 hours">
          <div className="px-4 py-5">
            <Sparkline data={dashboard.throughput} />
            <div className="numeric mt-3 flex justify-between text-[11px] text-muted-foreground">
              <span>07:00</span>
              <span>13:00</span>
              <span>19:00</span>
            </div>
          </div>
        </Panel>

        <Panel
          title="Live queue"
          meta={
            <Link to="/fulfillment" className="hover:text-foreground">
              All orders →
            </Link>
          }
        >
          <ul className="divide-y divide-border">
            {orders.slice(0, 5).map((o) => (
              <li
                key={o.id}
                className="flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-surface-2"
              >
                <span className="min-w-0">
                  <span className="numeric block text-sm font-medium">{o.id}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {o.seller} · {o.warehouse}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="numeric text-xs text-muted-foreground">
                    {o.slaHours === 0 ? "done" : `SLA ${o.slaHours}h`}
                  </span>
                  <StatusPill
                    tone={
                      o.stage === "SHIPPED"
                        ? "ok"
                        : o.stage === "PICKING"
                          ? "signal"
                          : o.stage === "PACKED"
                            ? "info"
                            : "neutral"
                    }
                  >
                    {o.stage}
                  </StatusPill>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel
        title="Recent activity"
        meta={
          <Link to="/audit" className="hover:text-foreground">
            Audit trail →
          </Link>
        }
      >
        <ul className="divide-y divide-border">
          {auditEvents.slice(0, 4).map((e) => (
            <li key={e.id} className="flex gap-4 px-4 py-3">
              <span className="numeric w-20 shrink-0 pt-0.5 text-[11px] text-muted-foreground">
                {e.time}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{e.action}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {e.subject}
                  {e.from ? ` · ${e.from} → ${e.to}` : ""} · {e.user}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="flex flex-wrap gap-2 border-t border-border pt-6">
        <Link to="/scanner">
          <Button variant="primary">Open scanner</Button>
        </Link>
        <Link to="/receiving">
          <Button>Log receipt</Button>
        </Link>
        <Link to="/inventory">
          <Button variant="ghost">Review low stock</Button>
        </Link>
      </div>
    </AppShell>
  );
}
