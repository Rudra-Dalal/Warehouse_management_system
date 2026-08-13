import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Input, EmptyState } from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { getReceivingRecordsApi, createReceivingRecordApi } from "@/api/receiving";
import { getSellersApi } from "@/api/sellers";
import { getProductsApi } from "@/api/products";
import { WarehouseId } from "@/types/wms";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/receiving")({
  head: () => ({
    meta: [
      { title: "Receiving — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Inbound shipments by warehouse with expected versus received counts and discrepancy flags.",
      },
    ],
  }),
  component: ReceivingPage,
});

const statusTone = (status: string) => {
  switch (status) {
    case "COMPLETED":
      return "ok";
    case "DISCREPANCY":
      return "danger";
    case "PENDING":
    default:
      return "signal";
  }
};

function ReceivingPage() {
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("receiving:write");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sellerId, setSellerId] = useState("");
  const [warehouseId, setWarehouseId] = useState<WarehouseId>("RENO");
  const [productId, setProductId] = useState("");
  const [qtyReceived, setQtyReceived] = useState<number>(0);
  const [notes, setNotes] = useState("");

  const { data: receivingRecords = [], isLoading, isError, error } = useQuery({
    queryKey: ["receiving"],
    queryFn: getReceivingRecordsApi,
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

  const productMap = useMemo(() => {
    const map = new Map<string, string>();
    products.forEach((p) => map.set(p.product_id, `${p.name} (${p.sku})`));
    return map;
  }, [products]);

  const createMutation = useMutation({
    mutationFn: createReceivingRecordApi,
    onSuccess: (record) => {
      toast.success(`Inbound Receipt logged successfully (${record.receiving_id})`);
      queryClient.invalidateQueries({ queryKey: ["receiving"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setIsModalOpen(false);
      setSellerId("");
      setProductId("");
      setQtyReceived(0);
      setNotes("");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to log receiving record.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sellerId || !productId || qtyReceived <= 0) {
      toast.error("Please select a seller, product, and valid received quantity.");
      return;
    }
    createMutation.mutate({
      seller_id: sellerId,
      warehouse_id: warehouseId,
      items: [
        {
          product_id: productId,
          quantity_received: Number(qtyReceived),
        },
      ],
      notes: notes.trim() || undefined,
    });
  };

  const discrepancies = receivingRecords.filter((r) => r.status === "DISCREPANCY").length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Receiving"
        description="Inbound shipments across Reno and Columbus, counted against seller manifests."
        actions={
          canWrite ? (
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus className="mr-1.5 size-4" /> Log receipt
            </Button>
          ) : undefined
        }
      />

      {discrepancies > 0 ? (
        <div className="anim-rise flex items-center gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
          <span className="size-1.5 rounded-full bg-danger" />
          <p className="text-sm">
            <span className="font-medium">{discrepancies} receiving discrepancies</span>{" "}
            <span className="text-muted-foreground">
              flagged in live database records.
            </span>
          </p>
        </div>
      ) : null}

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching inbound receiving logs...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">{(error as any)?.message || "Failed to load receiving records"}</p>
          </div>
        ) : receivingRecords.length === 0 ? (
          <EmptyState
            title="No receiving logs found"
            description="No inbound shipment receipts have been recorded yet."
          />
        ) : (
          <Table minWidth={760}>
            <THead
              cols={[
                { label: "Receiving ID", width: "18%" },
                { label: "Seller" },
                { label: "Warehouse" },
                { label: "Items Received", align: "right" },
                { label: "Received By" },
                { label: "Date" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {receivingRecords.map((r) => {
                const totalQty = r.items.reduce((sum, item) => sum + item.quantity_received, 0);
                return (
                  <Tr key={r.receiving_id}>
                    <Td className="numeric font-medium text-xs">{r.receiving_id}</Td>
                    <Td>{sellerMap.get(r.seller_id) || r.seller_id}</Td>
                    <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                      {r.warehouse_id}
                    </Td>
                    <Td align="right" className="numeric font-semibold">
                      {totalQty.toLocaleString()} units
                    </Td>
                    <Td className="text-muted-foreground">{r.received_by || "System"}</Td>
                    <Td className="numeric text-muted-foreground">
                      {new Date(r.received_at).toLocaleDateString()}
                    </Td>
                    <Td>
                      <StatusPill tone={statusTone(r.status)}>{r.status}</StatusPill>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}
        <TableFooter count={receivingRecords.length} total={receivingRecords.length} />
      </div>

      {/* Log Receipt Modal */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">Log Inbound Receipt</h3>
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
                  Destination Warehouse *
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
                  Product *
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
                  Quantity Received *
                </label>
                <Input
                  type="number"
                  min="1"
                  required
                  value={qtyReceived}
                  onChange={(e) => setQtyReceived(Number(e.target.value))}
                  placeholder="100"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Notes
                </label>
                <Input
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Pallet #3, dock 2 receipt"
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Logging..." : "Log Receipt"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
