import { createFileRoute } from "@tanstack/react-router";
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
import { getProductsApi, createProductApi } from "@/api/products";
import { getSellersApi } from "@/api/sellers";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/products")({
  head: () => ({
    meta: [
      { title: "Products — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "The seller catalog: SKUs, UPCs, categories and shipping weights maintained across the Whitfield network.",
      },
    ],
  }),
  component: ProductsPage,
});

function ProductsPage() {
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("product:write");

  const [query, setQuery] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  // New product form fields
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [upc, setUpc] = useState("");
  const [sellerId, setSellerId] = useState("");
  const [description, setDescription] = useState("");
  const [reorderPoint, setReorderPoint] = useState(50);

  const {
    data: products = [],
    isLoading,
    isError,
    error,
  } = useQuery({
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

  const createMutation = useMutation({
    mutationFn: createProductApi,
    onSuccess: (newProd) => {
      toast.success(`Product ${newProd.sku} created successfully!`);
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setIsModalOpen(false);
      // Reset form
      setSku("");
      setName("");
      setUpc("");
      setSellerId("");
      setDescription("");
      setReorderPoint(50);
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create product.");
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sku.trim() || !name.trim() || !upc.trim() || !sellerId) {
      toast.error("Please fill in SKU, Name, UPC, and Seller.");
      return;
    }
    createMutation.mutate({
      sku: sku.trim().toUpperCase(),
      name: name.trim(),
      upc: upc.trim(),
      seller_id: sellerId,
      description: description.trim() || undefined,
      reorder_point: Number(reorderPoint) || 0,
    });
  };

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter(
      (p) =>
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.upc.includes(q) ||
        (sellerMap.get(p.seller_id) || "").toLowerCase().includes(q),
    );
  }, [products, query, sellerMap]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Products"
        description="Master catalog records backed by real MongoDB database. Changes here trigger audit entries."
        actions={
          canWrite ? (
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus className="mr-1.5 size-4" /> New product
            </Button>
          ) : undefined
        }
      />

      <div className="relative max-w-md">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search product, SKU or UPC"
          className="pl-9"
        />
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching master product catalog...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load products"}
            </p>
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            title="No products found"
            description={
              query ? "No catalog record matches that query." : "No products available in database."
            }
          />
        ) : (
          <Table>
            <THead
              cols={[
                { label: "Product", width: "32%" },
                { label: "SKU" },
                { label: "UPC" },
                { label: "Seller" },
                { label: "Reorder Point", align: "right" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {rows.map((p) => (
                <Tr key={p.product_id || p.sku}>
                  <Td className="font-medium">{p.name}</Td>
                  <Td className="numeric text-muted-foreground">{p.sku}</Td>
                  <Td className="numeric text-muted-foreground">{p.upc}</Td>
                  <Td>{sellerMap.get(p.seller_id) || p.seller_id}</Td>
                  <Td align="right" className="numeric">
                    {p.reorder_point} units
                  </Td>
                  <Td>
                    <StatusPill tone={p.is_active ? "ok" : "neutral"}>
                      {p.is_active ? "Active" : "Archived"}
                    </StatusPill>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        <TableFooter count={rows.length} total={products.length} />
      </div>

      {/* New Product Modal */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Create Master Product
            </h3>
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  SKU *
                </label>
                <Input
                  required
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  placeholder="SKU-1001"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Product Name *
                </label>
                <Input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ergonomic Keyboard"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  UPC Barcode *
                </label>
                <Input
                  required
                  value={upc}
                  onChange={(e) => setUpc(e.target.value)}
                  placeholder="012345678905"
                  className="mt-1"
                />
              </div>

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
                  Reorder Point
                </label>
                <Input
                  type="number"
                  value={reorderPoint}
                  onChange={(e) => setReorderPoint(Number(e.target.value))}
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Description
                </label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional details"
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Save Product"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
