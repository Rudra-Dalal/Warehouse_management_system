import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { ScanLine, CornerDownLeft, RotateCcw } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Panel } from "@/components/whitfield/primitives";
import { inventory, type InventoryRow } from "@/lib/wms-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/scanner")({
  head: () => ({
    meta: [
      { title: "Barcode Scanner — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Scan or key a UPC to resolve a product and see live availability and reservations in Reno and Columbus.",
      },
      { property: "og:title", content: "Barcode Scanner — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Scan, resolve, act. Instant UPC lookup against live warehouse inventory.",
      },
    ],
  }),
  component: ScannerPage,
});

type Phase = "idle" | "resolving" | "found" | "notfound";

function ScannerPage() {
  const [value, setValue] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [row, setRow] = useState<InventoryRow | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const code = value.trim();
    if (!code) return;
    setPhase("resolving");
    window.setTimeout(() => {
      const match = inventory.find(
        (r) => r.upc === code || r.sku.toLowerCase() === code.toLowerCase(),
      );
      if (match) {
        setRow(match);
        setPhase("found");
      } else {
        setRow(null);
        setPhase("notfound");
      }
    }, 520);
  };

  const reset = () => {
    setValue("");
    setRow(null);
    setPhase("idle");
    inputRef.current?.focus();
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Barcode Scanner"
        description="Scan → resolve → product → inventory. Works with a handheld gun or keyboard entry."
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
                  phase === "notfound" && "bg-danger/10",
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
                  placeholder="Scan or enter UPC"
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
              {phase === "resolving" ? <StatusPill tone="signal">Resolving…</StatusPill> : null}
              {phase === "found" ? <StatusPill tone="ok">Product found</StatusPill> : null}
              {phase === "notfound" ? <StatusPill tone="danger">No match</StatusPill> : null}
              <span className="numeric ml-auto text-[11px] text-muted-foreground">
                Try 012345678905
              </span>
            </div>
          </div>
        </section>

        {/* Result */}
        <section className="min-h-[320px]">
          {phase === "found" && row ? (
            <div key={row.sku} className="anim-rise panel overflow-hidden">
              <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
                <div>
                  <p className="eyebrow">Product found</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">{row.name}</h2>
                  <p className="numeric mt-1.5 text-xs text-muted-foreground">
                    {row.sku} · UPC {row.upc} · {row.seller}
                  </p>
                </div>
                <StatusPill tone="ok">Resolved</StatusPill>
              </div>

              <div className="grid sm:grid-cols-2">
                {(["RENO", "COLUMBUS"] as const).map((w, i) => {
                  const data = w === "RENO" ? row.reno : row.columbus;
                  return (
                    <div
                      key={w}
                      className={cn(
                        "px-5 py-6",
                        i === 0 ? "border-b border-border sm:border-r sm:border-b-0" : "",
                      )}
                      style={{ animationDelay: `${i * 70}ms` }}
                    >
                      <p className="numeric text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                        {w}
                      </p>
                      <div className="mt-4 flex items-end gap-8">
                        <div>
                          <div className="numeric text-4xl leading-none font-semibold">
                            {data.available}
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground">available</div>
                        </div>
                        <div>
                          <div className="numeric text-4xl leading-none font-semibold text-muted-foreground">
                            {data.reserved}
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground">reserved</div>
                        </div>
                      </div>
                      <div className="mt-5 flex gap-2">
                        <Button size="sm">Adjust</Button>
                        <Button size="sm" variant="primary">
                          Reserve
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {phase === "notfound" ? (
            <div className="anim-rise panel flex flex-col items-center justify-center px-6 py-20 text-center">
              <p className="eyebrow text-danger">Unresolved code</p>
              <h2 className="mt-3 text-lg font-semibold">No product matches that UPC</h2>
              <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">
                Confirm the label is intact, then re-scan. Persistent mismatches should be raised
                against the seller's catalog.
              </p>
              <div className="mt-5 flex gap-2">
                <Button onClick={reset}>Scan again</Button>
                <Button variant="ghost">Report mismatch</Button>
              </div>
            </div>
          ) : null}

          {phase === "idle" || phase === "resolving" ? (
            <Panel title="Session" meta="This shift">
              <div className="grid grid-cols-3 divide-x divide-border">
                {[
                  ["48", "scans"],
                  ["46", "resolved"],
                  ["2", "mismatches"],
                ].map(([v, l]) => (
                  <div key={l} className="px-5 py-6">
                    <div className="numeric text-2xl leading-none font-semibold">{v}</div>
                    <div className="mt-2 text-xs text-muted-foreground">{l}</div>
                  </div>
                ))}
              </div>
              <div className="border-t border-border px-5 py-4">
                <p className="text-sm text-muted-foreground">
                  Scanner input is always focused — pull the trigger and the code lands here.
                </p>
              </div>
            </Panel>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
