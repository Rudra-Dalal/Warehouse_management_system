import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { ScanLine, CornerDownLeft, RotateCcw } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Panel } from "@/components/whitfield/primitives";
import { getProductByUpcApi, getProductBySkuApi } from "@/api/products";
import { getInventoryApi, adjustInventoryApi } from "@/api/inventory";
import { Product, Inventory, WarehouseId } from "@/types/wms";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/scanner")({
  head: () => ({
    meta: [
      { title: "Barcode Scanner — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Scan or key a UPC to resolve a product and see live availability and reservations in Reno and Columbus.",
      },
    ],
  }),
  component: ScannerPage,
});

type Phase = "idle" | "resolving" | "found" | "notfound";

function ScannerPage() {
  const { hasPermission } = useAuth();
  const canAdjust = hasPermission("inventory:adjust");

  const [value, setValue] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [product, setProduct] = useState<Product | null>(null);
  const [inventoryList, setInventoryList] = useState<Inventory[]>([]);
  const [scanStats, setScanStats] = useState({ scans: 0, resolved: 0, mismatches: 0 });

  const inputRef = useRef<HTMLInputElement>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const rawCode = value.trim();
    if (!rawCode) return;

    setPhase("resolving");
    setScanStats((prev) => ({ ...prev, scans: prev.scans + 1 }));

    // Normalize leading zeros if barcode scanner strips them
    const normalizedUpc = rawCode.padStart(12, "0");

    try {
      let foundProd: Product | null = null;

      // Try UPC lookup first
      try {
        foundProd = await getProductByUpcApi(rawCode);
      } catch {
        try {
          foundProd = await getProductByUpcApi(normalizedUpc);
        } catch {
          // Fallback to SKU lookup
          try {
            foundProd = await getProductBySkuApi(rawCode);
          } catch {
            foundProd = null;
          }
        }
      }

      if (foundProd) {
        setProduct(foundProd);
        // Fetch inventory levels
        const inv = await getInventoryApi({ product_id: foundProd.product_id });
        setInventoryList(inv);
        setPhase("found");
        setScanStats((prev) => ({ ...prev, resolved: prev.resolved + 1 }));
        toast.success(`Resolved ${foundProd.sku}: ${foundProd.name}`);
      } else {
        setProduct(null);
        setInventoryList([]);
        setPhase("notfound");
        setScanStats((prev) => ({ ...prev, mismatches: prev.mismatches + 1 }));
        toast.error(`No product matches barcode ${rawCode}`);
      }
    } catch (err: any) {
      setProduct(null);
      setInventoryList([]);
      setPhase("notfound");
      setScanStats((prev) => ({ ...prev, mismatches: prev.mismatches + 1 }));
    }
  };

  const reset = () => {
    setValue("");
    setProduct(null);
    setInventoryList([]);
    setPhase("idle");
    inputRef.current?.focus();
  };

  const handleQuickAdjust = async (warehouseId: WarehouseId, quantityDelta: number) => {
    if (!product) return;
    try {
      await adjustInventoryApi({
        warehouse_id: warehouseId,
        product_id: product.product_id,
        quantity_delta: quantityDelta,
        reason: "Scanner quick count update",
      });
      toast.success(`Updated ${warehouseId} stock by ${quantityDelta > 0 ? "+" : ""}${quantityDelta}`);
      const updatedInv = await getInventoryApi({ product_id: product.product_id });
      setInventoryList(updatedInv);
    } catch (err: any) {
      toast.error(err.message || "Failed to adjust inventory.");
    }
  };

  const renoData = inventoryList.find((i) => i.warehouse_id === "RENO") || {
    quantity_available: 0,
    quantity_reserved: 0,
  };
  const columbusData = inventoryList.find((i) => i.warehouse_id === "COLUMBUS") || {
    quantity_available: 0,
    quantity_reserved: 0,
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Barcode Scanner"
        description="Scan → resolve → product → inventory. Works with a handheld gun or manual keyboard entry."
        actions={
          <Button onClick={reset} variant="ghost">
            <RotateCcw className="size-4" /> Reset
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        {/* Scan console */}
        <section className="panel relative overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <p className="eyebrow">Scan product</p>
          </div>

          <div className="relative px-5 py-7">
            <div className="relative mx-auto flex h-32 w-full max-w-[300px] items-center justify-center overflow-hidden rounded-md border border-border-strong bg-surface-2">
              <div className="flex h-16 items-end gap-[3px]">
                {Array.from({ length: 34 }).map((_, i) => (
                  <span
                    key={i}
                    className="w-[3px] rounded-xs bg-foreground/70"
                    style={{ height: `${40 + ((i * 37) % 60)}%` }}
                  />
                ))}
              </div>
              {phase === "resolving" ? (
                <span className="scan-sweep absolute inset-x-0 h-10 bg-linear-to-b from-transparent via-signal/35 to-transparent" />
              ) : null}
              <span
                className={cn(
                  "absolute inset-0 transition-colors duration-300",
                  phase === "found" && "bg-ok/10",
                  phase === "notfound" && "bg-danger/10"
                )}
              />
            </div>

            <form onSubmit={submit} className="mt-6">
              <div className="relative">
                <ScanLine className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  ref={inputRef}
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value);
                    if (phase !== "idle") setPhase("idle");
                  }}
                  placeholder="Scan or enter UPC / SKU"
                  autoFocus
                  className="numeric h-12 w-full rounded-md border border-border bg-surface pr-10 pl-9 text-sm tracking-[0.08em] transition-colors focus:border-signal focus:outline-none"
                />
                <CornerDownLeft className="absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
              </div>
            </form>

            <div className="mt-4 flex items-center gap-2">
              {phase === "idle" ? (
                <StatusPill tone="neutral">
                  <span className="pulse-dot">Ready to scan</span>
                </StatusPill>
              ) : null}
              {phase === "resolving" ? <StatusPill tone="signal">Resolving live API...</StatusPill> : null}
              {phase === "found" ? <StatusPill tone="ok">Product found</StatusPill> : null}
              {phase === "notfound" ? <StatusPill tone="danger">No match</StatusPill> : null}
            </div>
          </div>
        </section>

        {/* Result */}
        <section className="min-h-[320px]">
          {phase === "found" && product ? (
            <div key={product.product_id} className="anim-rise panel overflow-hidden">
              <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
                <div>
                  <p className="eyebrow">Product found</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">{product.name}</h2>
                  <p className="numeric mt-1.5 text-xs text-muted-foreground">
                    {product.sku} · UPC {product.upc} · Reorder Point: {product.reorder_point}
                  </p>
                </div>
                <StatusPill tone="ok">Resolved</StatusPill>
              </div>

              <div className="grid sm:grid-cols-2">
                {[
                  { name: "RENO" as WarehouseId, data: renoData },
                  { name: "COLUMBUS" as WarehouseId, data: columbusData },
                ].map((w, i) => (
                  <div
                    key={w.name}
                    className={cn(
                      "px-5 py-6",
                      i === 0 ? "border-b border-border sm:border-r sm:border-b-0" : ""
                    )}
                  >
                    <p className="numeric text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                      {w.name} HUB
                    </p>
                    <div className="mt-4 flex items-end gap-8">
                      <div>
                        <div className="numeric text-4xl leading-none font-semibold">
                          {w.data.quantity_available.toLocaleString()}
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">available</div>
                      </div>
                      <div>
                        <div className="numeric text-4xl leading-none font-semibold text-muted-foreground">
                          {w.data.quantity_reserved.toLocaleString()}
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">reserved</div>
                      </div>
                    </div>
                    {canAdjust ? (
                      <div className="mt-5 flex gap-2">
                        <Button size="sm" onClick={() => handleQuickAdjust(w.name, 10)}>
                          +10 Count
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleQuickAdjust(w.name, -1)}>
                          -1 Count
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {phase === "notfound" ? (
            <div className="anim-rise panel flex flex-col items-center justify-center px-6 py-20 text-center">
              <p className="eyebrow text-danger">Unresolved barcode</p>
              <h2 className="mt-3 text-lg font-semibold">No product matches that UPC or SKU</h2>
              <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">
                Confirm the UPC label is scanned correctly or register the product in master catalog.
              </p>
              <div className="mt-5 flex gap-2">
                <Button onClick={reset}>Scan again</Button>
              </div>
            </div>
          ) : null}

          {phase === "idle" || phase === "resolving" ? (
            <Panel title="Session Activity" meta="Shift Scans">
              <div className="grid grid-cols-3 divide-x divide-border">
                {[
                  [String(scanStats.scans), "scans"],
                  [String(scanStats.resolved), "resolved"],
                  [String(scanStats.mismatches), "mismatches"],
                ].map(([v, l]) => (
                  <div key={l} className="px-5 py-6">
                    <div className="numeric text-2xl leading-none font-semibold">{v}</div>
                    <div className="mt-2 text-xs text-muted-foreground">{l}</div>
                  </div>
                ))}
              </div>
              <div className="border-t border-border px-5 py-4">
                <p className="text-sm text-muted-foreground">
                  Handheld USB/Bluetooth barcode scanner input automatically feeds into the field.
                </p>
              </div>
            </Panel>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
