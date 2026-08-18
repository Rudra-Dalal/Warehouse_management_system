import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, AlertCircle, Mic, MicOff, Check, X, Volume2, Sparkles } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  Button,
  StatusPill,
  Input,
  EmptyState,
} from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { getReceivingRecordsApi, createReceivingRecordApi } from "@/api/receiving";
import { getSellersApi } from "@/api/sellers";
import { getProductsApi } from "@/api/products";
import { executeVoiceCommandApi, VoiceCommandApiResponse } from "@/api/voice";
import { parseVoiceCommand } from "@/voice/command-parser";
import { WarehouseId } from "@/types/wms";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/receiving")({
  head: () => ({
    meta: [
      { title: "Receiving — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Inbound shipments by warehouse with expected versus received counts, voice receiving workflow, and discrepancy flags.",
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
  const { hasPermission, activeWarehouse } = useAuth();
  const canWrite = hasPermission("receiving:write");

  // Manual Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sellerId, setSellerId] = useState("");
  const [warehouseId, setWarehouseId] = useState<WarehouseId>("RENO");
  const [productId, setProductId] = useState("");
  const [qtyReceived, setQtyReceived] = useState<number>(0);
  const [notes, setNotes] = useState("");

  // Voice Receiving State
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voicePendingResponse, setVoicePendingResponse] = useState<VoiceCommandApiResponse | null>(
    null,
  );
  const [voiceEntities, setVoiceEntities] = useState<any>(null);
  const recognitionRef = useRef<any>(null);

  const {
    data: receivingRecords = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["receiving", activeWarehouse],
    queryFn: () => getReceivingRecordsApi(activeWarehouse || undefined),
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

  // Manual Inbound Mutation
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

  // Voice Command Mutation
  const voiceMutation = useMutation({
    mutationFn: executeVoiceCommandApi,
    onSuccess: (res) => {
      if (res.requires_confirmation || res.status === "confirmation_required") {
        setVoicePendingResponse(res);
      } else if (res.status === "success") {
        toast.success(res.message);
        queryClient.invalidateQueries({ queryKey: ["receiving"] });
        queryClient.invalidateQueries({ queryKey: ["inventory"] });
        setIsVoiceModalOpen(false);
        setVoicePendingResponse(null);
        setTranscript("");
        setVoiceEntities(null);
      } else {
        toast.error(res.message);
      }
    },
    onError: (err: any) => {
      toast.error(err.message || "Voice receiving operation failed.");
    },
  });

  // Speech Recognition Setup
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        const text = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join("");
        setTranscript(text);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setTranscript("");
      setVoicePendingResponse(null);
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (err) {
        console.warn("Could not start speech recognition:", err);
      }
    }
  };

  const handleVoiceParseAndSubmit = (text: string) => {
    if (!text.trim()) return;
    const parsed = parseVoiceCommand(text);
    const resolvedWh = parsed.entities.warehouse_id || (activeWarehouse as WarehouseId) || "RENO";
    const payloadEntities = {
      ...parsed.entities,
      warehouse_id: resolvedWh,
    };
    setVoiceEntities(payloadEntities);

    voiceMutation.mutate({
      transcript: text,
      intent: parsed.intent === "receive_inventory" ? "receive_inventory" : "receive_inventory",
      entities: payloadEntities,
      confirmed: false,
    });
  };

  const handleConfirmVoiceReceiving = () => {
    if (!voiceEntities) return;
    voiceMutation.mutate({
      transcript: transcript || "Confirmed voice receiving",
      intent: "receive_inventory",
      entities: voiceEntities,
      confirmed: true,
    });
  };

  const handleSubmitManual = (e: React.FormEvent) => {
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
        description="Inbound shipments across Reno and Columbus hubs, verified with voice AI and manual receipts."
        actions={
          canWrite ? (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setIsVoiceModalOpen(true);
                  setTranscript("");
                  setVoicePendingResponse(null);
                }}
                className="text-signal hover:bg-signal/10 border border-signal/30"
              >
                <Mic className="mr-1.5 size-4" /> Voice Inbound
              </Button>
              <Button variant="primary" onClick={() => setIsModalOpen(true)}>
                <Plus className="mr-1.5 size-4" /> Log receipt
              </Button>
            </div>
          ) : undefined
        }
      />

      {discrepancies > 0 ? (
        <div className="anim-rise flex items-center gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
          <span className="size-1.5 rounded-full bg-danger" />
          <p className="text-sm">
            <span className="font-medium">{discrepancies} receiving discrepancies</span>{" "}
            <span className="text-muted-foreground">flagged in live database records.</span>
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
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load receiving records"}
            </p>
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
                  <Tr key={r.receiving_reference || r.receiving_id || r.id}>
                    <Td className="numeric font-medium text-xs">
                      {r.receiving_reference || r.receiving_id || r.id}
                    </Td>
                    <Td>{sellerMap.get(r.seller_id) || r.seller_id}</Td>
                    <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                      {r.warehouse_code || r.warehouse_id}
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

      {/* Voice Receiving Confirmation Modal */}
      {isVoiceModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="grid size-8 place-items-center rounded-lg bg-signal/10 text-signal">
                  <Mic className="size-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">
                    Voice Inbound Receiving
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Speak or type your receipt command
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsVoiceModalOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>

            {/* Voice Control & Input */}
            <div className="space-y-3">
              <div className="flex items-center justify-center gap-3 p-4 rounded-xl border border-border bg-surface-2">
                <button
                  type="button"
                  onClick={toggleListening}
                  className={cn(
                    "grid size-14 place-items-center rounded-full transition-all cursor-pointer shadow-md",
                    isListening
                      ? "bg-danger text-white ring-4 ring-danger/20 scale-105 animate-pulse"
                      : "bg-signal text-signal-foreground hover:opacity-90",
                  )}
                >
                  {isListening ? <MicOff className="size-6" /> : <Mic className="size-6" />}
                </button>
                <div className="text-left">
                  <p className="text-xs font-semibold text-foreground">
                    {isListening ? "Listening... Speak clearly" : "Click mic to speak"}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    e.g. "Receive 50 units of SKU-1048 at Reno hub"
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <Input
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="Or type voice command manually..."
                  className="text-sm bg-background"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleVoiceParseAndSubmit(transcript)}
                  disabled={!transcript.trim() || voiceMutation.isPending}
                >
                  {voiceMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : "Parse"}
                </Button>
              </div>
            </div>

            {/* Confirmation Card (Authoritative Check Step) */}
            {voicePendingResponse && (
              <div className="anim-rise rounded-xl border border-signal/30 bg-signal/5 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-signal flex items-center gap-1.5">
                    <Sparkles className="size-3.5" /> Confirmation Required
                  </span>
                  <StatusPill tone="signal">Awaiting Authorization</StatusPill>
                </div>

                <p className="text-xs text-foreground/90 leading-relaxed font-medium">
                  {voicePendingResponse.message}
                </p>

                <div className="rounded-lg bg-surface border border-border/80 p-3 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Intent:</span>
                    <span className="font-mono font-medium">RECEIVE_INVENTORY</span>
                  </div>
                  {voiceEntities?.sku && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Product SKU:</span>
                      <span className="font-mono font-medium">{voiceEntities.sku}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Target Hub:</span>
                    <span className="font-mono font-medium">
                      {voiceEntities?.warehouse_id || activeWarehouse || "RENO"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Quantity to Receive:</span>
                    <span className="font-mono font-semibold text-ok">
                      +{voiceEntities?.quantity || 0} units
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <Button variant="ghost" size="sm" onClick={() => setVoicePendingResponse(null)}>
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleConfirmVoiceReceiving}
                    disabled={voiceMutation.isPending}
                    className="bg-ok hover:bg-ok/90 text-white"
                  >
                    {voiceMutation.isPending ? (
                      <Loader2 className="size-4 animate-spin mr-1.5" />
                    ) : (
                      <Check className="size-4 mr-1.5" />
                    )}
                    Confirm & Receive Stock
                  </Button>
                </div>
              </div>
            )}

            {!voicePendingResponse && (
              <div className="flex justify-end pt-1">
                <Button variant="ghost" size="sm" onClick={() => setIsVoiceModalOpen(false)}>
                  Close
                </Button>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Log Receipt Modal */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Log Inbound Receipt
            </h3>
            <form onSubmit={handleSubmitManual} className="space-y-4">
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
