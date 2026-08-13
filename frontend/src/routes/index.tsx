import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { Panel, StatusPill, Button } from "@/components/whitfield/primitives";
import { getInventoryApi } from "@/api/inventory";
import { getOrdersApi } from "@/api/orders";
import { getAuditLogsApi } from "@/api/audit";
import { getProductsApi } from "@/api/products";
import { getSellersApi } from "@/api/sellers";
import { OrderStatus } from "@/types/wms";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Whitfield Fulfillment — Warehouse Operations Dashboard" },
      {
        name: "description",
        content:
          "Live warehouse operations across Reno and Columbus: available units, active orders, SLA risk and receiving discrepancies at a glance.",
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

function Dashboard() {
  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const { data: inventory = [], isLoading: loadingInv } = useQuery({
    queryKey: ["inventory"],
    queryFn: () => getInventoryApi(),
  });

  const { data: orders = [], isLoading: loadingOrders } = useQuery({
    queryKey: ["orders"],
    queryFn: getOrdersApi,
  });

  const { data: auditLogs = [] } = useQuery({
    queryKey: ["audit"],
    queryFn: () => getAuditLogsApi({ limit: 5 }),
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: getProductsApi,
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

  // Calculations
  const totalAvailable = useMemo(
    () => inventory.reduce((sum, item) => sum + item.quantity_available, 0),
    [inventory]
  );

  const activeOrdersCount = useMemo(
    () => orders.filter((o) => o.status !== "SHIPPED" && o.status !== "CANCELLED").length,
    [orders]
  );

  const renoData = useMemo(() => {
    const renoItems = inventory.filter((i) => i.warehouse_id === "RENO");
    const avail = renoItems.reduce((s, i) => s + i.quantity_available, 0);
    const res = renoItems.reduce((s, i) => s + i.quantity_reserved, 0);
    const orderCount = orders.filter((o) => o.warehouse_id === "RENO" && o.status !== "SHIPPED").length;
    return { avail, res, orderCount };
  }, [inventory, orders]);

  const columbusData = useMemo(() => {
    const colItems = inventory.filter((i) => i.warehouse_id === "COLUMBUS");
    const avail = colItems.reduce((s, i) => s + i.quantity_available, 0);
    const res = colItems.reduce((s, i) => s + i.quantity_reserved, 0);
    const orderCount = orders.filter((o) => o.warehouse_id === "COLUMBUS" && o.status !== "SHIPPED").length;
    return { avail, res, orderCount };
  }, [inventory, orders]);

  const attentionItemsCount = useMemo(() => {
    // Count SKUs below reorder point
    let count = 0;
    products.forEach((p) => {
      const pInv = inventory.filter((i) => i.product_id === p.product_id);
      const avail = pInv.reduce((sum, item) => sum + item.quantity_available, 0);
      if (avail <= p.reorder_point) count++;
    });
    return count;
  }, [inventory, products]);

  const isLoading = loadingInv || loadingOrders;

  const stageTone = (s: OrderStatus) =>
    s === "SHIPPED"
      ? "ok"
      : s === "PACKED"
      ? "info"
      : s === "PICKING" || s === "RESERVED"
      ? "signal"
      : "neutral";

  return (
    <AppShell>
      <section className="anim-rise border-b border-border pb-8">
        <p className="eyebrow">Warehouse operations · {today}</p>
        <h1 className="display-xl mt-3">{greeting()}</h1>

        <div className="mt-9 grid gap-8 border-t border-border pt-8 sm:grid-cols-3">
          <div>
            <div className="numeric display-lg">
              {isLoading ? <Loader2 className="size-8 animate-spin" /> : totalAvailable.toLocaleString()}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">available units across network</p>
          </div>
          <div className="sm:border-l sm:border-border sm:pl-8">
            <div className="numeric display-lg">
              {isLoading ? <Loader2 className="size-8 animate-spin" /> : activeOrdersCount}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">active fulfillment orders</p>
          </div>
          <div className="sm:border-l sm:border-border sm:pl-8">
            <div className="numeric display-lg text-signal">
              {isLoading ? <Loader2 className="size-8 animate-spin" /> : attentionItemsCount}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">low stock SKUs need reorder</p>
          </div>
        </div>
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel title="Attention & Operational Quick Links" meta="Requires action this shift">
          <ul className="divide-y divide-border">
            {[
              { label: `${attentionItemsCount} SKUs below reorder point threshold`, to: "/inventory", tone: "bg-danger" },
              { label: `${activeOrdersCount} orders requiring pick/pack/ship`, to: "/fulfillment", tone: "bg-signal" },
              { label: "Scan UPC barcode to verify stock position", to: "/scanner", tone: "bg-info" },
            ].map((a) => (
              <li key={a.label}>
                <Link
                  to={a.to as any}
                  className="group flex items-center justify-between gap-4 px-4 py-4 transition-colors hover:bg-surface-2"
                >
                  <span className="flex items-center gap-3">
                    <span className={`size-1.5 rounded-full ${a.tone}`} />
                    <span className="text-sm font-medium">{a.label}</span>
                  </span>
                  <ArrowUpRight className="size-4 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Warehouse Hubs" meta="Available · reserved">
          <div className="divide-y divide-border">
            {[
              { name: "RENO HUB", avail: renoData.avail, res: renoData.res, orders: renoData.orderCount },
              { name: "COLUMBUS HUB", avail: columbusData.avail, res: columbusData.res, orders: columbusData.orderCount },
            ].map((w) => (
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
                      {w.avail.toLocaleString()}
                    </div>
                    <div className="mt-1.5 text-xs text-muted-foreground">available</div>
                  </div>
                  <div>
                    <div className="numeric text-2xl leading-none font-semibold text-muted-foreground">
                      {w.res.toLocaleString()}
                    </div>
                    <div className="mt-1.5 text-xs text-muted-foreground">reserved</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Panel
          title="Live Fulfillment Queue"
          meta={
            <Link to="/fulfillment" className="hover:text-foreground">
              All orders →
            </Link>
          }
        >
          {orders.length === 0 ? (
            <div className="p-6 text-xs text-muted-foreground">No active orders in fulfillment.</div>
          ) : (
            <ul className="divide-y divide-border">
              {orders.slice(0, 5).map((o) => (
                <li
                  key={o.order_id}
                  className="flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-surface-2"
                >
                  <span className="min-w-0">
                    <span className="numeric block text-sm font-medium">{o.order_id}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {sellerMap.get(o.seller_id) || o.seller_id} · {o.warehouse_id}
                    </span>
                  </span>
                  <StatusPill tone={stageTone(o.status)}>{o.status}</StatusPill>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Recent Audit Activity"
          meta={
            <Link to="/audit" className="hover:text-foreground">
              Audit trail →
            </Link>
          }
        >
          {auditLogs.length === 0 ? (
            <div className="p-6 text-xs text-muted-foreground">No recent audit events logged.</div>
          ) : (
            <ul className="divide-y divide-border">
              {auditLogs.slice(0, 5).map((e) => (
                <li key={e.audit_id} className="flex gap-4 px-4 py-3">
                  <span className="numeric w-20 shrink-0 pt-0.5 text-[11px] text-muted-foreground">
                    {new Date(e.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{e.action}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {e.entity_type}: {e.entity_id} · User: {e.user_id}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-border pt-6">
        <Link to="/scanner">
          <Button variant="primary">Open barcode scanner</Button>
        </Link>
        <Link to="/receiving">
          <Button>Log receiving receipt</Button>
        </Link>
        <Link to="/inventory">
          <Button variant="ghost">Review low stock</Button>
        </Link>
      </div>
    </AppShell>
  );
}
