import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill } from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { sellers } from "@/lib/wms-data";

export const Route = createFileRoute("/sellers")({
  head: () => ({
    meta: [
      { title: "Sellers — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Merchant accounts fulfilled by Whitfield: SKU counts, open orders and warehouse assignments.",
      },
      { property: "og:title", content: "Sellers — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Every merchant account, its catalog size and current order load.",
      },
    ],
  }),
  component: SellersPage,
});

function SellersPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Sellers"
        description="Merchant accounts, their catalog footprint and warehouse assignments."
        actions={<Button variant="primary">Onboard seller</Button>}
      />

      <div className="grid gap-6 sm:grid-cols-3">
        {[
          [String(sellers.length), "accounts"],
          [String(sellers.reduce((a, s) => a + s.skus, 0)), "SKUs managed"],
          [String(sellers.reduce((a, s) => a + s.openOrders, 0)), "open orders"],
        ].map(([v, l]) => (
          <div key={l} className="panel px-5 py-5">
            <div className="numeric text-3xl leading-none font-semibold">{v}</div>
            <div className="mt-2 text-xs text-muted-foreground">{l}</div>
          </div>
        ))}
      </div>

      <div className="panel overflow-hidden">
        <Table minWidth={760}>
          <THead
            cols={[
              { label: "Seller", width: "30%" },
              { label: "ID" },
              { label: "Contact" },
              { label: "SKUs", align: "right" },
              { label: "Open orders", align: "right" },
              { label: "Warehouses" },
              { label: "Status" },
            ]}
          />
          <tbody>
            {sellers.map((s) => (
              <Tr key={s.id}>
                <Td className="font-medium">{s.name}</Td>
                <Td className="numeric text-muted-foreground">{s.id}</Td>
                <Td className="text-muted-foreground">{s.contact}</Td>
                <Td align="right" className="numeric">
                  {s.skus}
                </Td>
                <Td align="right" className="numeric">
                  {s.openOrders}
                </Td>
                <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                  {s.warehouses.join(" · ")}
                </Td>
                <Td>
                  <StatusPill
                    tone={s.status === "active" ? "ok" : s.status === "onboarding" ? "info" : "neutral"}
                  >
                    {s.status}
                  </StatusPill>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
        <TableFooter count={sellers.length} total={sellers.length} />
      </div>
    </AppShell>
  );
}
