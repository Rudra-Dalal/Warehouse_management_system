/**
 * WMS Domain Models & Backend API Schema Definitions.
 * Aligned precisely with FastAPI backend models in core/models and core/apis/schemas.
 */

export type Role = "ADMIN" | "WAREHOUSE_MANAGER" | "INVENTORY_CLERK" | "READ_ONLY";

export type Permission =
  | "user:read"
  | "user:write"
  | "seller:read"
  | "seller:write"
  | "product:read"
  | "product:write"
  | "inventory:read"
  | "inventory:adjust"
  | "inventory:reserve"
  | "receiving:read"
  | "receiving:write"
  | "order:read"
  | "order:write"
  | "fulfillment:read"
  | "fulfillment:write"
  | "audit:read";

export interface User {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  permissions?: Permission[];
  assigned_warehouse_ids: string[];
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export type WarehouseId = "RENO" | "COLUMBUS";

export interface Warehouse {
  warehouse_id: WarehouseId;
  name: string;
  location: string;
  is_active: boolean;
}

export interface Seller {
  seller_id: string;
  name: string;
  code: string;
  contact_email: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Product {
  product_id: string;
  sku: string;
  name: string;
  upc: string;
  seller_id: string;
  description?: string | null;
  reorder_point: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Inventory {
  inventory_id: string;
  warehouse_id: WarehouseId;
  product_id: string;
  quantity_available: number;
  quantity_reserved: number;
  updated_at?: string;
}

export type MovementType = "RECEIVING" | "ADJUSTMENT" | "RESERVATION" | "FULFILLMENT" | "TRANSFER";

export interface InventoryMovement {
  movement_id: string;
  warehouse_id: WarehouseId;
  product_id: string;
  movement_type: MovementType;
  quantity_delta: number;
  previous_quantity: number;
  new_quantity: number;
  reason?: string | null;
  reference_id?: string | null;
  user_id: string;
  timestamp: string;
}

export interface Reservation {
  reservation_id: string;
  order_id: string;
  warehouse_id: WarehouseId;
  product_id: string;
  quantity_reserved: number;
  status: "ACTIVE" | "RELEASED" | "FULFILLED";
  created_at: string;
  updated_at?: string;
}

export interface ReceivingItem {
  product_id: string;
  quantity_received: number;
  quantity_expected?: number;
  notes?: string;
}

export interface ReceivingRecord {
  receiving_id: string;
  seller_id: string;
  warehouse_id: WarehouseId;
  status: "PENDING" | "COMPLETED" | "DISCREPANCY";
  items: ReceivingItem[];
  received_by: string;
  notes?: string | null;
  received_at: string;
  created_at?: string;
}

export interface OrderItem {
  product_id: string;
  quantity: number;
  unit_price?: number;
}

export type OrderStatus =
  "PENDING" | "CONFIRMED" | "RESERVED" | "PICKING" | "PACKED" | "SHIPPED" | "CANCELLED";

export interface Order {
  order_id: string;
  seller_id: string;
  warehouse_id: WarehouseId;
  customer_name: string;
  shipping_address: string;
  status: OrderStatus;
  items: OrderItem[];
  created_at: string;
  updated_at?: string;
}

export type FulfillmentStep = "PICK" | "PACK" | "SHIP";

export interface FulfillmentRecord {
  fulfillment_id: string;
  order_id: string;
  warehouse_id: WarehouseId;
  action: FulfillmentStep;
  performed_by: string;
  timestamp: string;
  notes?: string | null;
}

export interface AuditLog {
  audit_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_id: string;
  warehouse_id?: WarehouseId | null;
  previous_state?: Record<string, any> | null;
  new_state?: Record<string, any> | null;
  metadata?: Record<string, any> | null;
  timestamp: string;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg: string;
  type?: string;
}

export interface BackendErrorResponse {
  detail?: string | ApiErrorDetail[];
  message?: string;
  error?: string;
}
