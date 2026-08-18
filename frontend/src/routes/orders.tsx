import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, Loader2, AlertCircle } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  Button,
  Input,
  StatusPill,
  EmptyState,
} from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { getOrdersApi, createOrderApi } from "@/api/orders";
import { getSellersApi } from "@/api/sellers";
import { getProductsApi } from "@/api/products";
import { OrderStatus, WarehouseId } from "@/types/wms";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/orders")({
  head: () => ({
    meta: [
      { title: "Orders — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Every order in the network with seller, warehouse, unit counts, SLA pressure and current stage.",
      },
    ],
  }),
  component: OrdersPage,
});

const ORDER_STAGES: (OrderStatus | "ALL")[] = [
  "ALL",
  "PENDING",
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

function OrdersPage() {
  const queryClient = useQueryClient();
  const { hasPermission, activeWarehouse } = useAuth();
  const canWrite = hasPermission("order:write");

  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<OrderStatus | "ALL">("ALL");

  // Create Order Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sellerId, setSellerId] = useState("");
  const [warehouseId, setWarehouseId] = useState<WarehouseId>("RENO");
  const [customerName, setCustomerName] = useState("");
  const [shippingAddress, setShippingAddress] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState<number>(1);

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

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: getProductsApi,
  });

  const sellerMap = useMemo(() => {
    const map = new Map<string, string>();
    sellers.forEach((s) => map.set(s.seller_id, s.name));
    return map;
  }, [sellers]);

  const createMutation = useMutation({
    mutationFn: createOrderApi,
    onSuccess: (newOrder) => {
      toast.success(`Order ${newOrder.order_id} created successfully!`);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      setIsModalOpen(false);
      setSellerId("");
      setCustomerName("");
      setShippingAddress("");
      setProductId("");
      setQuantity(1);
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create order.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !sellerId ||
      !customerName.trim() ||
      !shippingAddress.trim() ||
      !productId ||
      quantity <= 0
    ) {
      toast.error("Please fill in seller, customer, address, product, and valid quantity.");
      return;
    }
    createMutation.mutate({
      seller_id: sellerId,
      warehouse_id: warehouseId,
      customer_name: customerName.trim(),
      shipping_address: shippingAddress.trim(),
      items: [
        {
          product_id: productId,
          quantity: Number(quantity),
        },
      ],
    });
  };

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return orders.filter(
      (o) =>
        (stage === "ALL" || o.status === stage) &&
        (!q ||
          o.order_id.toLowerCase().includes(q) ||
          (sellerMap.get(o.seller_id) || "").toLowerCase().includes(q) ||
          o.customer_name.toLowerCase().includes(q) ||
          o.shipping_address.toLowerCase().includes(q)),
    );
  }, [orders, query, stage, sellerMap]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Orders"
        description="The full order book. Open an order in Fulfillment to advance its stage."
        actions={
          <div className="flex gap-2">
            {canWrite ? (
              <Button variant="primary" onClick={() => setIsModalOpen(true)}>
                <Plus className="mr-1.5 size-4" /> Create order
              </Button>
            ) : null}
            <Link to="/fulfillment">
              <Button variant="ghost">Open fulfillment</Button>
            </Link>
          </div>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search order ID, seller or customer"
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface p-1">
          {ORDER_STAGES.map((s) => (
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
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching active order book...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load orders"}
            </p>
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            title="No orders in this view"
            description="Clear search or filter selection to view more orders."
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
                { label: "Order ID", width: "16%" },
                { label: "Seller" },
                { label: "Customer" },
                { label: "Warehouse" },
                { label: "Line Items", align: "right" },
                { label: "Total Units", align: "right" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {rows.map((o) => {
                const totalUnits = o.items.reduce((sum, item) => sum + item.quantity, 0);
                return (
                  <Tr key={o.order_id}>
                    <Td className="numeric font-medium text-xs">{o.order_id}</Td>
                    <Td>{sellerMap.get(o.seller_id) || o.seller_id}</Td>
                    <Td className="text-muted-foreground">{o.customer_name}</Td>
                    <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                      {o.warehouse_id}
                    </Td>
                    <Td align="right" className="numeric">
                      {o.items.length}
                    </Td>
                    <Td align="right" className="numeric font-semibold">
                      {totalUnits}
                    </Td>
                    <Td>
                      <StatusPill tone={stageTone(o.status)}>{o.status}</StatusPill>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}
        <TableFooter count={rows.length} total={orders.length} />
      </div>

      {/* Create Order Modal */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Create Customer Order
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Seller *
                </label>
                <select
                  required
                  value={sellerId}
                  onChange={(e) => setSellerId(e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  <option value="">Select Seller</option>
                  {sellers.map((s) => (
                    <option key={s.seller_id} value={s.seller_id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Warehouse *
                </label>
                <select
                  value={warehouseId}
                  onChange={(e) => setWarehouseId(e.target.value as WarehouseId)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  <option value="RENO">Reno Hub</option>
                  <option value="COLUMBUS">Columbus Hub</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Customer Name *
                </label>
                <Input
                  required
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="John Doe"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Shipping Address *
                </label>
                <Input
                  required
                  value={shippingAddress}
                  onChange={(e) => setShippingAddress(e.target.value)}
                  placeholder="123 Main St, Reno NV 89501"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Product Item *
                </label>
                <select
                  required
                  value={productId}
                  onChange={(e) => setProductId(e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  <option value="">Select Product</option>
                  {products.map((p) => (
                    <option key={p.product_id} value={p.product_id}>
                      {p.name} ({p.sku})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Quantity *
                </label>
                <Input
                  type="number"
                  min="1"
                  required
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Place Order"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
