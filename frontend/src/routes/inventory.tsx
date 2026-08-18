import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  StatusPill,
  Button,
  Input,
  EmptyState,
} from "@/components/whitfield/primitives";
import { cn } from "@/lib/utils";
import { getProductsApi } from "@/api/products";
import { getInventoryApi, adjustInventoryApi, reserveInventoryApi } from "@/api/inventory";
import { getSellersApi } from "@/api/sellers";
import { WarehouseId, Product } from "@/types/wms";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Per-SKU availability and reservations across Reno and Columbus, with reorder thresholds and contextual adjustments.",
      },
    ],
  }),
  component: InventoryPage,
});

const WAREHOUSES: WarehouseId[] = ["RENO", "COLUMBUS"];
const FILTERS = ["All", "Low stock", "Critical"] as const;

function InventoryPage() {
  const queryClient = useQueryClient();
  const { hasPermission, activeWarehouse } = useAuth();
  const canAdjust = hasPermission("inventory:adjust");
  const canReserve = hasPermission("inventory:reserve");

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [warehouse, setWarehouse] = useState<WarehouseId | "ALL">("ALL");

  // Adjustment & Reservation Modal States
  const [adjustModalProduct, setAdjustModalProduct] = useState<Product | null>(null);
  const [adjustWarehouse, setAdjustWarehouse] = useState<WarehouseId>("RENO");
  const [delta, setDelta] = useState<number>(0);
  const [reason, setReason] = useState("");

  const [reserveModalProduct, setReserveModalProduct] = useState<Product | null>(null);
  const [reserveWarehouse, setReserveWarehouse] = useState<WarehouseId>("RENO");
  const [reserveOrderId, setReserveOrderId] = useState("");
  const [reserveQuantity, setReserveQuantity] = useState<number>(1);

  // Queries
  const { data: products = [], isLoading: loadingProducts } = useQuery({
    queryKey: ["products"],
    queryFn: getProductsApi,
  });

  const {
    data: inventory = [],
    isLoading: loadingInventory,
    isError,
    error,
  } = useQuery({
    queryKey: ["inventory", activeWarehouse],
    queryFn: () => getInventoryApi({ warehouse_code: activeWarehouse || undefined }),
  });

  const { data: sellers = [] } = useQuery({
    queryKey: ["sellers"],
    queryFn: getSellersApi,
  });

  const sellerMap = useMemo(() => {
    const map = new Map<string, string>();
    sellers.forEach((s) => map.set(s.seller_id, s.name));
    return map;
  }, [sellers]);

  // Aggregate inventory by product_id -> { reno: { available, reserved }, columbus: { available, reserved } }
  const inventoryByProduct = useMemo(() => {
    const map = new Map<
      string,
      {
        reno: { available: number; reserved: number };
        columbus: { available: number; reserved: number };
      }
    >();

    inventory.forEach((inv) => {
      let entry = map.get(inv.product_id);
      if (!entry) {
        entry = {
          reno: { available: 0, reserved: 0 },
          columbus: { available: 0, reserved: 0 },
        };
        map.set(inv.product_id, entry);
      }
      if (inv.warehouse_id === "RENO") {
        entry.reno.available = inv.quantity_available;
        entry.reno.reserved = inv.quantity_reserved;
      } else if (inv.warehouse_id === "COLUMBUS") {
        entry.columbus.available = inv.quantity_available;
        entry.columbus.reserved = inv.quantity_reserved;
      }
    });

    return map;
  }, [inventory]);

  // Mutations
  const adjustMutation = useMutation({
    mutationFn: adjustInventoryApi,
    onSuccess: () => {
      toast.success("Inventory adjusted successfully.");
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setAdjustModalProduct(null);
      setDelta(0);
      setReason("");
    },
    onError: (err: any) => {
      if (err.status === 409) {
        toast.error("Conflict: The available quantity changed or was modified concurrently.");
      } else {
        toast.error(err.message || "Failed to adjust inventory.");
      }
    },
  });

  const reserveMutation = useMutation({
    mutationFn: reserveInventoryApi,
    onSuccess: () => {
      toast.success("Inventory reserved successfully.");
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setReserveModalProduct(null);
      setReserveOrderId("");
      setReserveQuantity(1);
    },
    onError: (err: any) => {
      if (err.status === 409) {
        toast.error(
          "Reservation unavailable: The available quantity changed before your request completed.",
        );
      } else {
        toast.error(err.message || "Failed to reserve inventory.");
      }
    },
  });

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter((p) => {
      const invData = inventoryByProduct.get(p.product_id) || {
        reno: { available: 0, reserved: 0 },
        columbus: { available: 0, reserved: 0 },
      };

      const totalAvail = invData.reno.available + invData.columbus.available;
      const isLow = totalAvail <= p.reorder_point;
      const isCritical = totalAvail === 0;

      const matches =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.upc.includes(q) ||
        (sellerMap.get(p.seller_id) || "").toLowerCase().includes(q);

      const byFilter =
        filter === "All" ||
        (filter === "Low stock" && isLow) ||
        (filter === "Critical" && isCritical);

      const byWarehouse =
        warehouse === "ALL" ||
        (warehouse === "RENO" ? invData.reno.available > 0 : invData.columbus.available > 0);

      return matches && byFilter && byWarehouse;
    });
  }, [products, query, filter, warehouse, inventoryByProduct, sellerMap]);

  const isLoading = loadingProducts || loadingInventory;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Inventory"
        description="Availability and reservations per SKU, compared across warehouses backed by real MongoDB state."
        actions={
          <Button
            variant="ghost"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["inventory"] })}
          >
            <RefreshCw className="mr-1.5 size-4" /> Refresh
          </Button>
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
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching real-time inventory levels...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load inventory"}
            </p>
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            title="No SKUs match this view"
            description="Adjust search or filters to broaden results."
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
                  <Th className="text-right">Total Available</Th>
                  <Th className="text-right">Total Reserved</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => {
                  const invData = inventoryByProduct.get(p.product_id) || {
                    reno: { available: 0, reserved: 0 },
                    columbus: { available: 0, reserved: 0 },
                  };

                  const totalAvail = invData.reno.available + invData.columbus.available;
                  const totalRes = invData.reno.reserved + invData.columbus.reserved;
                  const isLow = totalAvail <= p.reorder_point && totalAvail > 0;
                  const isCritical = totalAvail === 0;

                  return (
                    <tr
                      key={p.product_id}
                      className="group border-b border-border last:border-0 transition-colors hover:bg-surface-2/70"
                    >
                      <td className="px-4 py-3.5">
                        <div className="font-medium">{p.name}</div>
                        <div className="numeric mt-0.5 text-[11px] text-muted-foreground">
                          {p.sku} · UPC {p.upc} · {sellerMap.get(p.seller_id) || "Seller"}
                        </div>
                      </td>
                      <WarehouseCell
                        available={invData.reno.available}
                        reserved={invData.reno.reserved}
                      />
                      <WarehouseCell
                        available={invData.columbus.available}
                        reserved={invData.columbus.reserved}
                      />
                      <td className="numeric px-4 py-3.5 text-right font-semibold">
                        {totalAvail.toLocaleString()}
                      </td>
                      <td className="numeric px-4 py-3.5 text-right text-muted-foreground">
                        {totalRes.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusPill tone={isCritical ? "danger" : isLow ? "warn" : "ok"}>
                          {isCritical ? "Out of Stock" : isLow ? "Low Stock" : "In Stock"}
                        </StatusPill>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <span className="inline-flex gap-1">
                          {canAdjust ? (
                            <Button size="sm" onClick={() => setAdjustModalProduct(p)}>
                              Adjust
                            </Button>
                          ) : null}
                          {canReserve ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setReserveModalProduct(p)}
                            >
                              Reserve
                            </Button>
                          ) : null}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Adjust Inventory Modal */}
      {adjustModalProduct ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Adjust Stock — {adjustModalProduct.name}
            </h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                adjustMutation.mutate({
                  warehouse_id: adjustWarehouse,
                  product_id: adjustModalProduct.product_id,
                  quantity_delta: Number(delta),
                  reason: reason.trim() || undefined,
                });
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Warehouse
                </label>
                <select
                  value={adjustWarehouse}
                  onChange={(e) => setAdjustWarehouse(e.target.value as WarehouseId)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  <option value="RENO">Reno Hub</option>
                  <option value="COLUMBUS">Columbus Hub</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Quantity Delta (+ or -)
                </label>
                <Input
                  type="number"
                  required
                  value={delta}
                  onChange={(e) => setDelta(Number(e.target.value))}
                  placeholder="e.g. 50 or -10"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Reason
                </label>
                <Input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Cycle count, damage, audit correction"
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setAdjustModalProduct(null)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={adjustMutation.isPending}>
                  {adjustMutation.isPending ? "Submitting..." : "Apply Adjustment"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Reserve Inventory Modal */}
      {reserveModalProduct ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Reserve Stock — {reserveModalProduct.name}
            </h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                reserveMutation.mutate({
                  order_id: reserveOrderId.trim(),
                  warehouse_id: reserveWarehouse,
                  product_id: reserveModalProduct.product_id,
                  quantity: Number(reserveQuantity),
                });
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Order ID *
                </label>
                <Input
                  required
                  value={reserveOrderId}
                  onChange={(e) => setReserveOrderId(e.target.value)}
                  placeholder="ORD-9901"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Warehouse
                </label>
                <select
                  value={reserveWarehouse}
                  onChange={(e) => setReserveWarehouse(e.target.value as WarehouseId)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  <option value="RENO">Reno Hub</option>
                  <option value="COLUMBUS">Columbus Hub</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Quantity to Reserve *
                </label>
                <Input
                  type="number"
                  min="1"
                  required
                  value={reserveQuantity}
                  onChange={(e) => setReserveQuantity(Number(e.target.value))}
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setReserveModalProduct(null)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={reserveMutation.isPending}>
                  {reserveMutation.isPending ? "Reserving..." : "Reserve Units"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
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
