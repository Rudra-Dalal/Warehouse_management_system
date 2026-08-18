import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { AppShell } from "@/components/whitfield/app-shell";
import {
  PageHeader,
  Button,
  StatusPill,
  Input,
  EmptyState,
} from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { getUsersApi, createUserApi } from "@/api/users";
import { Role } from "@/types/wms";
import { toast } from "sonner";
import { useAuth } from "@/auth/auth-context";

export const Route = createFileRoute("/users")({
  head: () => ({
    meta: [
      { title: "Users — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Role-based access across the warehouse network: admins, managers, operators and viewers with warehouse scope.",
      },
    ],
  }),
  component: UsersPage,
});

const ROLES: Role[] = ["ADMIN", "WAREHOUSE_MANAGER", "INVENTORY_CLERK", "READ_ONLY"];

const roleTone = (role: Role) => {
  switch (role) {
    case "ADMIN":
      return "signal";
    case "WAREHOUSE_MANAGER":
      return "info";
    case "INVENTORY_CLERK":
      return "ok";
    case "READ_ONLY":
    default:
      return "neutral";
  }
};

function UsersPage() {
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canManage = hasPermission("user:write");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("INVENTORY_CLERK");

  const {
    data: usersList = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["users"],
    queryFn: getUsersApi,
  });

  const createMutation = useMutation({
    mutationFn: createUserApi,
    onSuccess: (newUser) => {
      toast.success(`User ${newUser.username} created successfully!`);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setIsModalOpen(false);
      setUsername("");
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("INVENTORY_CLERK");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create user account.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim() || !fullName.trim() || !password.trim()) {
      toast.error("Please fill in all required user fields.");
      return;
    }
    createMutation.mutate({
      username: username.trim(),
      email: email.trim(),
      full_name: fullName.trim(),
      password,
      role,
    });
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Users"
        description="Role-based access control. User identity and permissions backed by MongoDB."
        actions={
          canManage ? (
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus className="mr-1.5 size-4" /> Create user
            </Button>
          ) : undefined
        }
      />

      <div className="panel overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-8 animate-spin text-signal" />
            <p className="mt-3 text-sm font-mono">Fetching user accounts &amp; roles...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-12 text-danger">
            <AlertCircle className="size-8" />
            <p className="mt-3 text-sm font-medium">
              {(error as any)?.message || "Failed to load users"}
            </p>
          </div>
        ) : usersList.length === 0 ? (
          <EmptyState title="No user accounts" description="No users found in database." />
        ) : (
          <Table minWidth={720}>
            <THead
              cols={[
                { label: "User", width: "26%" },
                { label: "Email" },
                { label: "Role" },
                { label: "User ID" },
                { label: "Status" },
              ]}
            />
            <tbody>
              {usersList.map((u) => {
                const initials = (u.full_name || u.username)
                  .split(" ")
                  .map((p) => p[0])
                  .join("")
                  .toUpperCase()
                  .slice(0, 2);

                return (
                  <Tr key={u.user_id || u.email}>
                    <Td>
                      <span className="flex items-center gap-2.5">
                        <span className="grid size-7 place-items-center rounded-full bg-surface-2 text-[11px] font-semibold">
                          {initials}
                        </span>
                        <span className="font-medium">{u.full_name || u.username}</span>
                      </span>
                    </Td>
                    <Td className="text-muted-foreground">{u.email}</Td>
                    <Td>
                      <StatusPill tone={roleTone(u.role)}>{u.role}</StatusPill>
                    </Td>
                    <Td className="numeric text-xs text-muted-foreground">{u.user_id}</Td>
                    <Td>
                      <StatusPill tone={u.is_active ? "ok" : "danger"}>
                        {u.is_active ? "Active" : "Disabled"}
                      </StatusPill>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}
        <TableFooter count={usersList.length} total={usersList.length} />
      </div>

      {/* Create User Modal */}
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold tracking-tight text-foreground">
              Create User Account
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Username *
                </label>
                <Input
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="johndoe"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Full Name *
                </label>
                <Input
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Email Address *
                </label>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@whitfield.com"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Password *
                </label>
                <Input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Role Assignment *
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Save User"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
