import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  Button,
  StatusPill,
  Panel,
  EmptyState,
} from "@/components/whitfield/primitives";
import { getOrdersApi } from "@/api/orders";
import { pickOrderApi, packOrderApi, shipOrderApi } from "@/api/fulfillment";
import { getSellersApi } from "@/api/sellers";
import { Order, OrderStatus } from "@/types/wms";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/fulfillment")({
  head: () => ({
    meta: [
      { title: "Fulfillment — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Track every order through confirmed, reserved, picking, packed and shipped with SLA pressure surfaced first.",
      },
    ],
  }),
  component: FulfillmentPage,
});

const FULFILLMENT_PIPELINE: OrderStatus[] = [
  "CONFIRMED",
  "RESERVED",
  "PICKING",
  "PACKED",
  "SHIPPED",
];

const stageTone = (s: OrderStatus) =>
  s === "SHIPPED"
    ? "ok"
    : s === "PACKED"
      ? "info"
      : s === "PICKING" || s === "RESERVED"
        ? "signal"
        : "neutral";

function FulfillmentPage() {
  const queryClient = useQueryClient();
  const { hasPermission, activeWarehouse } = useAuth();
  const canWrite = hasPermission("fulfillment:write");

  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const {
    data: orders = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["orders", activeWarehouse],
    queryFn: () => getOrdersApi(activeWarehouse || undefined),
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

  const selectedOrder = useMemo(() => {
    if (!orders.length) return null;
    if (selectedOrderId) {
      const match = orders.find((o) => o.order_id === selectedOrderId);
      if (match) return match;
    }
    return orders[0];
  }, [orders, selectedOrderId]);

  const counts = FULFILLMENT_PIPELINE.map((stage) => ({
    stage,
    count: orders.filter((o) => o.status === stage).length,
  }));

  // Fulfillment Mutations
  const pickMutation = useMutation({
    mutationFn: pickOrderApi,
    onSuccess: (rec) => {
      toast.success(`Order ${rec.order_id} picked successfully.`);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to pick order."),
  });

  const packMutation = useMutation({
    mutationFn: packOrderApi,
    onSuccess: (rec) => {
      toast.success(`Order ${rec.order_id} packed successfully.`);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to pack order."),
  });

  const shipMutation = useMutation({
    mutationFn: shipOrderApi,
    onSuccess: (rec) => {
      toast.success(`Order ${rec.order_id} shipped successfully!`);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to ship order."),
  });

  const handleAdvance = (order: Order) => {
    if (!canWrite) {
      toast.error("You don't have permission to modify fulfillment state.");
      return;
    }

    if (order.status === "RESERVED" || order.status === "CONFIRMED") {
      pickMutation.mutate({ order_id: order.order_id, warehouse_id: order.warehouse_id });
    } else if (order.status === "PICKING") {
      packMutation.mutate({ order_id: order.order_id, warehouse_id: order.warehouse_id });
    } else if (order.status === "PACKED") {
      shipMutation.mutate({ order_id: order.order_id, warehouse_id: order.warehouse_id });
    }
  };

  const isPending = pickMutation.isPending || packMutation.isPending || shipMutation.isPending;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Fulfillment"
        description="Orders progress through confirmed, reserved, picking, packed and shipped states in live MongoDB."
        actions={
          <Button
            variant="ghost"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["orders"] })}
          >
            <RefreshCw className="mr-1.5 size-4" /> Refresh Pipeline
          </Button>
        }
      />

      {/* Pipeline Header */}
      <div className="panel overflow-x-auto">
        <div className="flex min-w-[720px] divide-x divide-border">
          {counts.map(({ stage, count }) => {
            const active = selectedOrder?.status === stage;
            const currentIdx = selectedOrder
              ? FULFILLMENT_PIPELINE.indexOf(selectedOrder.status)
              : -1;
            const passed = FULFILLMENT_PIPELINE.indexOf(stage) < currentIdx;
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
        <Panel title="Order Queue" meta={`${orders.length} total orders`}>
          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
              <Loader2 className="size-8 animate-spin text-signal" />
              <p className="mt-3 text-sm font-mono">Loading fulfillment queue...</p>
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-12 text-danger">
              <AlertCircle className="size-8" />
              <p className="mt-3 text-sm font-medium">
                {(error as any)?.message || "Failed to load orders"}
              </p>
            </div>
          ) : orders.length === 0 ? (
            <EmptyState
              title="No orders in queue"
              description="Create an order in Orders page to begin fulfillment."
            />
          ) : (
            <ul className="divide-y divide-border">
              {orders.map((o) => {
                const totalUnits = o.items.reduce((sum, i) => sum + i.quantity, 0);
                const isSelected = selectedOrder?.order_id === o.order_id;
                return (
                  <li key={o.order_id}>
                    <button
                      onClick={() => setSelectedOrderId(o.order_id)}
                      className={cn(
                        "flex w-full items-center gap-4 px-4 py-3.5 text-left transition-colors",
                        isSelected ? "bg-surface-2" : "hover:bg-surface-2/60",
                      )}
                    >
                      <span
                        className={cn(
                          "h-8 w-[2px] rounded-full transition-colors",
                          isSelected ? "bg-signal" : "bg-transparent",
                        )}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="numeric block text-sm font-medium">{o.order_id}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {sellerMap.get(o.seller_id) || o.seller_id} · {o.items.length} lines ·{" "}
                          {totalUnits} units · {o.warehouse_id}
                        </span>
                      </span>
                      <StatusPill tone={stageTone(o.status)}>{o.status}</StatusPill>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        {selectedOrder ? (
          <OrderDetail
            order={selectedOrder}
            sellerName={sellerMap.get(selectedOrder.seller_id) || selectedOrder.seller_id}
            onAdvance={() => handleAdvance(selectedOrder)}
            isPending={isPending}
            canWrite={canWrite}
          />
        ) : (
          <div className="panel flex items-center justify-center p-12 text-muted-foreground text-sm">
            Select an order to view fulfillment details.
          </div>
        )}
      </div>
    </AppShell>
  );
}

function OrderDetail({
  order,
  sellerName,
  onAdvance,
  isPending,
  canWrite,
}: {
  order: Order;
  sellerName: string;
  onAdvance: () => void;
  isPending: boolean;
  canWrite: boolean;
}) {
  const currentIdx = FULFILLMENT_PIPELINE.indexOf(order.status);
  const totalUnits = order.items.reduce((sum, i) => sum + i.quantity, 0);

  let nextAction = "";
  if (order.status === "CONFIRMED" || order.status === "RESERVED") {
    nextAction = "Pick Order";
  } else if (order.status === "PICKING") {
    nextAction = "Pack Order";
  } else if (order.status === "PACKED") {
    nextAction = "Ship Order";
  }

  return (
    <section key={order.order_id} className="anim-rise panel h-fit overflow-hidden">
      <div className="border-b border-border px-5 py-4">
        <p className="eyebrow">Selected Order</p>
        <h2 className="numeric mt-2 text-xl font-semibold tracking-tight">{order.order_id}</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {sellerName} · Destination: {order.customer_name}, {order.shipping_address}
        </p>
      </div>

      <ol className="px-5 py-5">
        {FULFILLMENT_PIPELINE.map((s, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          return (
            <li key={s} className="relative flex gap-3.5 pb-5 last:pb-0">
              {i < FULFILLMENT_PIPELINE.length - 1 ? (
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
                    Current stage · {totalUnits} units across {order.items.length} line items
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="grid grid-cols-3 divide-x divide-border border-t border-border">
        {[
          [String(totalUnits), "units"],
          [String(order.items.length), "line items"],
          [order.warehouse_id, "hub"],
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
        {nextAction && canWrite ? (
          <Button variant="primary" disabled={isPending} onClick={onAdvance}>
            {isPending ? "Updating..." : `Advance: ${nextAction}`}
          </Button>
        ) : (
          <Button variant="ghost" disabled>
            {order.status === "SHIPPED" ? "Fulfillment Completed" : "View Only"}
          </Button>
        )}
      </div>
    </section>
  );
}
