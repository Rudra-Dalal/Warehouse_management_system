import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/whitfield/app-shell";
import { PageHeader, Button, StatusPill } from "@/components/whitfield/primitives";
import { Table, THead, Tr, Td, TableFooter } from "@/components/whitfield/table";
import { users } from "@/lib/wms-data";

export const Route = createFileRoute("/users")({
  head: () => ({
    meta: [
      { title: "Users — Whitfield Fulfillment" },
      {
        name: "description",
        content:
          "Role-based access across the warehouse network: admins, managers, operators and viewers with warehouse scope.",
      },
      { property: "og:title", content: "Users — Whitfield Fulfillment" },
      {
        property: "og:description",
        content: "Who can do what, in which warehouse. RBAC at a glance.",
      },
    ],
  }),
  component: UsersPage,
});

function UsersPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Users"
        description="Role-based access control. Every role change is recorded in the audit trail."
        actions={<Button variant="primary">Invite user</Button>}
      />

      <div className="panel overflow-hidden">
        <Table minWidth={720}>
          <THead
            cols={[
              { label: "User", width: "26%" },
              { label: "Email" },
              { label: "Role" },
              { label: "Warehouse scope" },
              { label: "Last active" },
              { label: "Status" },
            ]}
          />
          <tbody>
            {users.map((u) => (
              <Tr key={u.email}>
                <Td>
                  <span className="flex items-center gap-2.5">
                    <span className="grid size-7 place-items-center rounded-full bg-surface-2 text-[11px] font-semibold">
                      {u.name
                        .split(" ")
                        .map((p) => p[0])
                        .join("")
                        .slice(0, 2)}
                    </span>
                    <span className="font-medium">{u.name}</span>
                  </span>
                </Td>
                <Td className="text-muted-foreground">{u.email}</Td>
                <Td>
                  <StatusPill
                    tone={
                      u.role === "Admin"
                        ? "signal"
                        : u.role === "Manager"
                          ? "info"
                          : u.role === "Operator"
                            ? "ok"
                            : "neutral"
                    }
                  >
                    {u.role}
                  </StatusPill>
                </Td>
                <Td className="numeric text-[11px] tracking-wider text-muted-foreground">
                  {u.warehouses === "ALL" ? "ALL" : u.warehouses.join(" · ")}
                </Td>
                <Td className="text-muted-foreground">{u.lastActive}</Td>
                <Td>
                  <StatusPill
                    tone={u.status === "active" ? "ok" : u.status === "invited" ? "warn" : "danger"}
                  >
                    {u.status}
                  </StatusPill>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
        <TableFooter count={users.length} total={users.length} />
      </div>
    </AppShell>
  );
}
