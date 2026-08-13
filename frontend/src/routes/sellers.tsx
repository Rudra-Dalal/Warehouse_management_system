import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill, Input, EmptyState } from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { getSellersApi, createSellerApi } from "@/api/sellers";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/sellers")({
  head: () => ({
    meta: [
      { title: "Sellers — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Merchant accounts fulfilled by Whitfield: SKU counts, open orders and warehouse assignments.",
      },
    ],
  }),
  component: SellersPage,
});

function SellersPage() {
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("seller:write");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");

  const { data: sellers = [], isLoading, isError, error } = useQuery({
    queryKey: ["sellers"],
    queryFn: getSellersApi,
  });

  const createMutation = useMutation({
    mutationFn: createSellerApi,
    onSuccess: (newSeller) => {
      toast.success(`Seller ${newSeller.name} onboarded successfully!`);
      queryClient.invalidateQueries({ queryKey: ["sellers"] });
      setIsModalOpen(false);
      setName("");
      setCode("");
      setEmail("");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to onboard seller.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !code.trim() || !email.trim()) {
      toast.error("Please fill in seller name, code, and contact email.");
      return;
    }
    createMutation.mutate({
      name: name.trim(),
      code: code.trim().toUpperCase(),
      contact_email: email.trim(),
    });
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Catalog"
        title="Sellers"
        description="Merchant accounts, their catalog footprint and warehouse assignments."
        actions={
          canWrite ? (
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus className="mr-1.5 size-4" /> Onboard seller
            </Button>
          ) : undefined
        }
      />

      <div className="grid gap-6 sm:grid-cols-3">
        {[
          [String(sellers.length), "active accounts"],
          ["RENO & COLUMBUS", "assigned hubs"],
          ["ACTIVE", "operating status"],
        ].map(([v, l]) => (
          <div key={l} className="panel px-5 py-5">
            <div className="numeric text-3xl leading-none font-semibold">{v}</div>
            <div className="mt-2 text-xs text-muted-foreground">{l}</div>
          </div>
        ))}
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching active seller accounts...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">{(error as any)?.message || "Failed to load sellers"}</p>
          </div>
        ) : sellers.length === 0 ? (
          <EmptyState
            title="No sellers onboarded"
            description="No merchant accounts have been registered in the database yet."
          />
        ) : (
          <Table minWidth={760}>
            <THead
              cols={[
                { label: "Seller Name", width: "30%" },
                { label: "Code" },
                { label: "Contact Email" },
                { label: "Seller ID" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {sellers.map((s) => (
                <Tr key={s.seller_id}>
                  <Td className="font-medium">{s.name}</Td>
                  <Td className="numeric text-muted-foreground">{s.code}</Td>
                  <Td className="text-muted-foreground">{s.contact_email}</Td>
                  <Td className="numeric text-xs text-muted-foreground">{s.seller_id}</Td>
                  <Td>
                    <StatusPill tone={s.is_active ? "ok" : "neutral"}>
                      {s.is_active ? "Active" : "Inactive"}
                    </StatusPill>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        <TableFooter count={sellers.length} total={sellers.length} />
      </div>

      {/* Modal for creating a seller */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">Onboard Merchant Account</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Seller Name *
                </label>
                <Input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Apex Trading Ltd"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Seller Code *
                </label>
                <Input
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="APEX"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Contact Email *
                </label>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="logistics@apex.com"
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Save Seller"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
