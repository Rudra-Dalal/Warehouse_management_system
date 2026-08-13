import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill } from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { receipts } from "@/lib/wms-data";

export const Route = createFileRoute("/receiving")({
  head: () => ({
    meta: [
      { title: "Receiving — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Inbound shipments by warehouse with expected versus received counts and discrepancy flags.",
      },
      { property: "og:title", content: "Receiving — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Inbound dock activity, unit counts and discrepancies in one view.",
      },
    ],
  }),
  component: ReceivingPage,
});

const tone = (s: string) =>
  s === "closed" ? "ok" : s === "discrepancy" ? "danger" : s === "in_progress" ? "signal" : "neutral";

function ReceivingPage() {
  const discrepancies = receipts.filter((r) => r.status === "discrepancy").length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Receiving"
        description="Inbound shipments across Reno and Columbus, counted against seller manifests."
        actions={
          <>
            <Button>Manifest import</Button>
            <Button variant="primary">Log receipt</Button>
          </>
        }
      />

      {discrepancies > 0 ? (
        <div className="anim-rise flex items-center gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
          <span className="size-1.5 rounded-full bg-danger" />
          <p className="text-sm">
            <span className="font-medium">{discrepancies} receiving discrepancies</span>{" "}
            <span className="text-muted-foreground">
              awaiting reconciliation with the seller manifest.
            </span>
          </p>
          <Button size="sm" className="ml-auto">
            Review
          </Button>
        </div>
      ) : null}

      <div className="panel overflow-hidden">
        <Table minWidth={760}>
          <THead
            cols={[
              { label: "Receipt", width: "18%" },
              { label: "Seller" },
              { label: "Warehouse" },
              { label: "Expected", align: "right" },
              { label: "Received", align: "right" },
              { label: "Variance", align: "right" },
              { label: "Arrived" },
              { label: "Status" },
            ]}
          />
          <tbody>
            {receipts.map((r) => {
              const variance = r.received - r.expected;
              return (
                <Tr key={r.id}>
                  <Td className="numeric font-medium">{r.id}</Td>
                  <Td>{r.seller}</Td>
                  <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                    {r.warehouse}
                  </Td>
                  <Td align="right" className="numeric">
                    {r.expected}
                  </Td>
                  <Td align="right" className="numeric">
                    {r.received}
                  </Td>
                  <Td
                    align="right"
                    className={
                      variance === 0
                        ? "numeric text-muted-foreground"
                        : "numeric font-medium text-danger"
                    }
                  >
                    {variance === 0 ? "—" : variance}
                  </Td>
                  <Td className="numeric text-muted-foreground">{r.arrived}</Td>
                  <Td>
                    <StatusPill tone={tone(r.status)}>{r.status.replace("_", " ")}</StatusPill>
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
        <TableFooter count={receipts.length} total={receipts.length} />
      </div>
    </AppShell>
  );
}
