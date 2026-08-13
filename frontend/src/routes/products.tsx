import { createFileRoute } from "@tanstack/react-router";
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
import { products } from "@/lib/wms-data";

export const Route = createFileRoute("/products")({
  head: () => ({
    meta: [
      { title: "Products — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "The seller catalog: SKUs, UPCs, categories and shipping weights maintained across the Whitfield network.",
      },
      { property: "og:title", content: "Products — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Catalog of every SKU handled by Whitfield, with UPC and seller attribution.",
      },
    ],
  }),
  component: ProductsPage,
});

function ProductsPage() {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter(
      (p) =>
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.upc.includes(q) ||
        p.seller.toLowerCase().includes(q),
    );
  }, [query]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Products"
        description="Master catalog records. Changes here are versioned in the audit trail."
        actions={<Button variant="primary">New product</Button>}
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
        {rows.length === 0 ? (
          <EmptyState
            title="No products found"
            description="No catalog record matches that term. Check the SKU or UPC and try again."
          />
        ) : (
          <Table>
            <THead
              cols={[
                { label: "Product", width: "32%" },
                { label: "SKU" },
                { label: "UPC" },
                { label: "Seller" },
                { label: "Category" },
                { label: "Weight", align: "right" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {rows.map((p) => (
                <Tr key={p.sku}>
                  <Td className="font-medium">{p.name}</Td>
                  <Td className="numeric text-muted-foreground">{p.sku}</Td>
                  <Td className="numeric text-muted-foreground">{p.upc}</Td>
                  <Td>{p.seller}</Td>
                  <Td className="text-muted-foreground">{p.category}</Td>
                  <Td align="right" className="numeric">
                    {p.weightLb.toFixed(1)} lb
                  </Td>
                  <Td>
                    <StatusPill tone={p.active ? "ok" : "neutral"}>
                      {p.active ? "Active" : "Archived"}
                    </StatusPill>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        <TableFooter count={rows.length} total={products.length} />
      </div>
    </AppShell>
  );
}
