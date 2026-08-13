import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  StatusPill,
  Button,
  Input,
  EmptyState,
} from "@/components/whitfield/primitives";
import {
  inventory,
  stockState,
  totalAvailable,
  totalReserved,
  WAREHOUSES,
  type Warehouse,
} from "@/lib/wms-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Per-SKU availability and reservations across Reno and Columbus, with reorder thresholds and contextual adjustments.",
      },
      { property: "og:title", content: "Inventory — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Dense, precise stock positions across every Whitfield warehouse.",
      },
    ],
  }),
  component: InventoryPage,
});

const FILTERS = ["All", "Low stock", "Critical"] as const;

function InventoryPage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [warehouse, setWarehouse] = useState<Warehouse | "ALL">("ALL");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return inventory.filter((r) => {
      const matches =
        !q ||
        r.name.toLowerCase().includes(q) ||
        r.sku.toLowerCase().includes(q) ||
        r.upc.includes(q) ||
        r.seller.toLowerCase().includes(q);
      const state = stockState(r);
      const byFilter =
        filter === "All" ||
        (filter === "Low stock" && state !== "healthy") ||
        (filter === "Critical" && state === "critical");
      const byWarehouse =
        warehouse === "ALL" ||
        (warehouse === "RENO" ? r.reno.available > 0 : r.columbus.available > 0);
      return matches && byFilter && byWarehouse;
    });
  }, [query, filter, warehouse]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Inventory"
        description="Availability and reservations per SKU, compared across warehouses."
        actions={
          <>
            <Button>Export</Button>
            <Button variant="primary">Adjust stock</Button>
          </>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search SKU, UPC, product or seller"
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-sm px-2.5 py-1.5 text-xs font-medium transition-colors",
                filter === f
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1">
          {(["ALL", ...WAREHOUSES] as const).map((w) => (
            <button
              key={w}
              onClick={() => setWarehouse(w)}
              className={cn(
                "numeric rounded-sm px-2.5 py-1.5 text-[11px] tracking-wider transition-colors",
                warehouse === w
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {w}
            </button>
          ))}
        </div>

        <Button variant="ghost" size="md" className="shrink-0">
          <SlidersHorizontal className="size-4" /> Filters
        </Button>
      </div>

      <div className="panel overflow-hidden">
        {rows.length === 0 ? (
          <EmptyState
            title="No SKUs match this view"
            description="Adjust the search term, stock filter or warehouse selection to widen the result set."
            action={
              <Button
                onClick={() => {
                  setQuery("");
                  setFilter("All");
                  setWarehouse("ALL");
                }}
              >
                Reset filters
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-2/60">
                  <Th className="w-[34%]">Product</Th>
                  <Th className="text-right">Reno</Th>
                  <Th className="text-right">Columbus</Th>
                  <Th className="text-right">Available</Th>
                  <Th className="text-right">Reserved</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const state = stockState(r);
                  return (
                    <tr
                      key={r.sku}
                      className="group border-b border-border last:border-0 transition-colors hover:bg-surface-2/70"
                    >
                      <td className="px-4 py-3.5">
                        <div className="font-medium">{r.name}</div>
                        <div className="numeric mt-0.5 text-[11px] text-muted-foreground">
                          {r.sku} · UPC {r.upc} · {r.seller}
                        </div>
                      </td>
                      <WarehouseCell available={r.reno.available} reserved={r.reno.reserved} />
                      <WarehouseCell
                        available={r.columbus.available}
                        reserved={r.columbus.reserved}
                      />
                      <td className="numeric px-4 py-3.5 text-right font-semibold">
                        {totalAvailable(r).toLocaleString()}
                      </td>
                      <td className="numeric px-4 py-3.5 text-right text-muted-foreground">
                        {totalReserved(r).toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusPill
                          tone={
                            state === "healthy" ? "ok" : state === "low" ? "warn" : "danger"
                          }
                        >
                          {state === "healthy" ? "In stock" : state === "low" ? "Low" : "Critical"}
                        </StatusPill>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <span className="inline-flex gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
                          <Button size="sm">Adjust</Button>
                          <Button size="sm" variant="ghost">
                            History
                          </Button>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          <p className="numeric text-[11px] tracking-wider text-muted-foreground uppercase">
            {rows.length} of {inventory.length} SKUs
          </p>
          <div className="flex items-center gap-1">
            <Button size="sm" variant="ghost" disabled>
              Previous
            </Button>
            <span className="numeric px-2 text-xs text-muted-foreground">Page 1 / 1</span>
            <Button size="sm" variant="ghost" disabled>
              Next
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={cn(
        "px-4 py-2.5 text-left font-mono text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase",
        className,
      )}
    >
      {children}
    </th>
  );
}

function WarehouseCell({ available, reserved }: { available: number; reserved: number }) {
  return (
    <td className="px-4 py-3.5 text-right">
      <div className="numeric font-medium">{available.toLocaleString()}</div>
      <div className="numeric text-[11px] text-muted-foreground">{reserved} res</div>
    </td>
  );
}
