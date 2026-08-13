import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  Button,
  Input,
  StatusPill,
  EmptyState,
} from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { orders, FULFILLMENT_STAGES, type Stage } from "@/lib/wms-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/orders")({
  head: () => ({
    meta: [
      { title: "Orders — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Every order in the network with seller, warehouse, unit counts, SLA pressure and current stage.",
      },
      { property: "og:title", content: "Orders — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Search and filter the full order book across Reno and Columbus.",
      },
    ],
  }),
  component: OrdersPage,
});

const stageTone = (s: Stage) =>
  s === "SHIPPED" ? "ok" : s === "PACKED" ? "info" : s === "PICKING" ? "signal" : "neutral";

function OrdersPage() {
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<Stage | "ALL">("ALL");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return orders.filter(
      (o) =>
        (stage === "ALL" || o.stage === stage) &&
        (!q ||
          o.id.toLowerCase().includes(q) ||
          o.seller.toLowerCase().includes(q) ||
          o.destination.toLowerCase().includes(q)),
    );
  }, [query, stage]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Orders"
        description="The full order book. Open an order in Fulfillment to advance its stage."
        actions={
          <Link to="/fulfillment">
            <Button variant="primary">Open fulfillment</Button>
          </Link>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search order, seller or destination"
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface p-1">
          {(["ALL", ...FULFILLMENT_STAGES] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStage(s)}
              className={cn(
                "numeric rounded-sm px-2.5 py-1.5 text-[11px] tracking-wider transition-colors",
                stage === s
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="panel overflow-hidden">
        {rows.length === 0 ? (
          <EmptyState
            title="No orders in this view"
            description="Clear the search or choose a different stage to see more of the order book."
            action={
              <Button
                onClick={() => {
                  setQuery("");
                  setStage("ALL");
                }}
              >
                Reset
              </Button>
            }
          />
        ) : (
          <Table minWidth={820}>
            <THead
              cols={[
                { label: "Order", width: "16%" },
                { label: "Seller" },
                { label: "Destination" },
                { label: "Warehouse" },
                { label: "Lines", align: "right" },
                { label: "Units", align: "right" },
                { label: "SLA", align: "right" },
                { label: "Stage" },
              ]}
            />
            <tbody>
              {rows.map((o) => (
                <Tr key={o.id}>
                  <Td className="numeric font-medium">{o.id}</Td>
                  <Td>{o.seller}</Td>
                  <Td className="text-muted-foreground">{o.destination}</Td>
                  <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                    {o.warehouse}
                  </Td>
                  <Td align="right" className="numeric">
                    {o.lines}
                  </Td>
                  <Td align="right" className="numeric">
                    {o.units}
                  </Td>
                  <Td
                    align="right"
                    className={cn(
                      "numeric",
                      o.slaHours > 0 && o.slaHours <= 2
                        ? "text-danger"
                        : o.slaHours <= 4
                          ? "text-warn"
                          : "text-muted-foreground",
                    )}
                  >
                    {o.slaHours === 0 ? "—" : `${o.slaHours}h`}
                  </Td>
                  <Td>
                    <StatusPill tone={stageTone(o.stage)}>{o.stage}</StatusPill>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        <TableFooter count={rows.length} total={orders.length} />
      </div>
    </AppShell>
  );
}
