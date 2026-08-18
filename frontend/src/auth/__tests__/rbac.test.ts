import { describe, it, expect } from "vitest";
import { hasRole, hasPermission } from "../rbac";
import { User } from "@/types/wms";

const adminUser: User = {
  user_id: "u1",
  username: "admin",
  email: "admin@whitfield.com",
  full_name: "Admin User",
  role: "ADMIN",
  assigned_warehouse_ids: ["RENO", "COLUMBUS"],
  is_active: true,
};

const clerkUser: User = {
  user_id: "u2",
  username: "clerk",
  email: "clerk@whitfield.com",
  full_name: "Clerk User",
  role: "INVENTORY_CLERK",
  assigned_warehouse_ids: ["RENO"],
  is_active: true,
};

const inactiveUser: User = {
  user_id: "u3",
  username: "inactive",
  email: "inactive@whitfield.com",
  full_name: "Inactive User",
  role: "ADMIN",
  assigned_warehouse_ids: ["RENO"],
  is_active: false,
};

describe("RBAC Utilities", () => {
  it("should evaluate hasRole correctly", () => {
    expect(hasRole(adminUser, "ADMIN")).toBe(true);
    expect(hasRole(adminUser, ["ADMIN", "WAREHOUSE_MANAGER"])).toBe(true);
    expect(hasRole(clerkUser, "ADMIN")).toBe(false);
    expect(hasRole(null, "ADMIN")).toBe(false);
    expect(hasRole(inactiveUser, "ADMIN")).toBe(false);
  });

  it("should evaluate hasPermission correctly for Admin", () => {
    expect(hasPermission(adminUser, "user:read")).toBe(true);
    expect(hasPermission(adminUser, "inventory:adjust")).toBe(true);
  });

  it("should evaluate hasPermission correctly for Inventory Clerk", () => {
    expect(hasPermission(clerkUser, "inventory:adjust")).toBe(true);
    expect(hasPermission(clerkUser, "user:write")).toBe(false);
    expect(hasPermission(clerkUser, "seller:write")).toBe(false);
  });
});
