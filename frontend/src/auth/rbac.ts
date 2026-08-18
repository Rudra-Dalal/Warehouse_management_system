/**
 * Role-Based Access Control (RBAC) frontend utilities.
 * Note: Frontend RBAC is purely for UX and feature visibility.
 * Backend authorization is always authoritative.
 */

import { Role, Permission, User } from "@/types/wms";

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  ADMIN: [
    "user:read",
    "user:write",
    "seller:read",
    "seller:write",
    "product:read",
    "product:write",
    "inventory:read",
    "inventory:adjust",
    "inventory:reserve",
    "receiving:read",
    "receiving:write",
    "order:read",
    "order:write",
    "fulfillment:read",
    "fulfillment:write",
    "audit:read",
  ],
  WAREHOUSE_MANAGER: [
    "seller:read",
    "seller:write",
    "product:read",
    "product:write",
    "inventory:read",
    "inventory:adjust",
    "inventory:reserve",
    "receiving:read",
    "receiving:write",
    "order:read",
    "order:write",
    "fulfillment:read",
    "fulfillment:write",
    "audit:read",
  ],
  INVENTORY_CLERK: [
    "product:read",
    "inventory:read",
    "inventory:adjust",
    "receiving:read",
    "receiving:write",
    "fulfillment:read",
    "fulfillment:write",
  ],
  READ_ONLY: [
    "product:read",
    "inventory:read",
    "seller:read",
    "order:read",
    "receiving:read",
    "audit:read",
  ],
};

export function hasRole(user: User | null, roles: Role | Role[]): boolean {
  if (!user || !user.is_active) return false;
  const roleList = Array.isArray(roles) ? roles : [roles];
  return roleList.includes(user.role);
}

export function hasPermission(user: User | null, permission: Permission): boolean {
  if (!user || !user.is_active) return false;

  // If user object carries backend granted permissions array, use that
  if (user.permissions && Array.isArray(user.permissions) && user.permissions.length > 0) {
    return user.permissions.includes(permission);
  }

  // Fallback to role mapping
  const granted = ROLE_PERMISSIONS[user.role] || [];
  return granted.includes(permission);
}
