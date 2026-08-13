/**
 * Local demo fixtures for the Whitfield UI skeleton.
 * These mirror the shapes returned by the FastAPI/MongoDB WMS backend
 * (users, sellers, products, inventory, receiving, orders, fulfillment,
 * audit). They exist only so the interface can be designed and reviewed —
 * no fake API layer, no alternative backend.
 */

export const WAREHOUSES = ["RENO", "COLUMBUS"] as const;
export type Warehouse = (typeof WAREHOUSES)[number];

export type InventoryRow = {
  sku: string;
  name: string;
  upc: string;
  seller: string;
  reno: { available: number; reserved: number };
  columbus: { available: number; reserved: number };
  reorderPoint: number;
};

export const inventory: InventoryRow[] = [
  {
    sku: "SKU-1048",
    name: "Wireless Keyboard",
    upc: "012345678905",
    seller: "Northgate Supply",
    reno: { available: 120, reserved: 18 },
    columbus: { available: 84, reserved: 12 },
    reorderPoint: 60,
  },
  {
    sku: "SKU-2210",
    name: "USB-C Hub 7-Port",
    upc: "012345671122",
    seller: "Northgate Supply",
    reno: { available: 42, reserved: 30 },
    columbus: { available: 16, reserved: 9 },
    reorderPoint: 75,
  },
  {
    sku: "SKU-3391",
    name: "Ergonomic Mouse Pad",
    upc: "018345678331",
    seller: "Cobalt Trading",
    reno: { available: 610, reserved: 44 },
    columbus: { available: 388, reserved: 21 },
    reorderPoint: 150,
  },
  {
    sku: "SKU-4477",
    name: '27" 4K Monitor',
    upc: "090345678447",
    seller: "Cobalt Trading",
    reno: { available: 28, reserved: 22 },
    columbus: { available: 9, reserved: 7 },
    reorderPoint: 40,
  },
  {
    sku: "SKU-5512",
    name: "Laptop Stand Aluminium",
    upc: "011145678551",
    seller: "Harbor Line Goods",
    reno: { available: 233, reserved: 12 },
    columbus: { available: 141, reserved: 4 },
    reorderPoint: 80,
  },
  {
    sku: "SKU-6603",
    name: "Noise Cancelling Headset",
    upc: "013395678660",
    seller: "Harbor Line Goods",
    reno: { available: 74, reserved: 51 },
    columbus: { available: 33, reserved: 18 },
    reorderPoint: 90,
  },
  {
    sku: "SKU-7719",
    name: "Thermal Label Roll 4x6",
    upc: "015555678771",
    seller: "Northgate Supply",
    reno: { available: 1420, reserved: 210 },
    columbus: { available: 980, reserved: 140 },
    reorderPoint: 400,
  },
  {
    sku: "SKU-8842",
    name: "Barcode Scanner Gun",
    upc: "017775678884",
    seller: "Cobalt Trading",
    reno: { available: 12, reserved: 10 },
    columbus: { available: 4, reserved: 3 },
    reorderPoint: 25,
  },
];

export const totalAvailable = (r: InventoryRow) =>
  r.reno.available + r.columbus.available;
export const totalReserved = (r: InventoryRow) =>
  r.reno.reserved + r.columbus.reserved;

export type StockState = "healthy" | "low" | "critical";
export const stockState = (r: InventoryRow): StockState => {
  const a = totalAvailable(r);
  if (a < r.reorderPoint * 0.5) return "critical";
  if (a < r.reorderPoint) return "low";
  return "healthy";
};

export const FULFILLMENT_STAGES = [
  "CONFIRMED",
  "RESERVED",
  "PICKING",
  "PACKED",
  "SHIPPED",
] as const;
export type Stage = (typeof FULFILLMENT_STAGES)[number];

export type Order = {
  id: string;
  seller: string;
  warehouse: Warehouse;
  units: number;
  lines: number;
  stage: Stage;
  slaHours: number;
  placed: string;
  destination: string;
};

export const orders: Order[] = [
  { id: "ORD-10482", seller: "Northgate Supply", warehouse: "RENO", units: 5, lines: 2, stage: "PICKING", slaHours: 3, placed: "09:12", destination: "Sacramento, CA" },
  { id: "ORD-10483", seller: "Cobalt Trading", warehouse: "COLUMBUS", units: 22, lines: 6, stage: "RESERVED", slaHours: 7, placed: "09:20", destination: "Cleveland, OH" },
  { id: "ORD-10484", seller: "Harbor Line Goods", warehouse: "RENO", units: 3, lines: 1, stage: "CONFIRMED", slaHours: 11, placed: "09:41", destination: "Boise, ID" },
  { id: "ORD-10485", seller: "Northgate Supply", warehouse: "COLUMBUS", units: 48, lines: 9, stage: "PACKED", slaHours: 2, placed: "08:04", destination: "Pittsburgh, PA" },
  { id: "ORD-10486", seller: "Cobalt Trading", warehouse: "RENO", units: 14, lines: 4, stage: "PICKING", slaHours: 1, placed: "07:55", destination: "Reno, NV" },
  { id: "ORD-10487", seller: "Harbor Line Goods", warehouse: "COLUMBUS", units: 9, lines: 3, stage: "SHIPPED", slaHours: 0, placed: "06:30", destination: "Detroit, MI" },
  { id: "ORD-10488", seller: "Northgate Supply", warehouse: "RENO", units: 61, lines: 12, stage: "RESERVED", slaHours: 5, placed: "10:02", destination: "Salt Lake City, UT" },
  { id: "ORD-10489", seller: "Cobalt Trading", warehouse: "COLUMBUS", units: 2, lines: 1, stage: "CONFIRMED", slaHours: 9, placed: "10:18", destination: "Columbus, OH" },
];

export type Product = {
  sku: string;
  name: string;
  upc: string;
  seller: string;
  category: string;
  weightLb: number;
  active: boolean;
};

const CATEGORIES = ["Peripherals", "Accessories", "Displays", "Consumables"];
const WEIGHTS = [1.2, 0.8, 0.4, 12.6, 2.1, 0.9, 3.4, 1.7];

export const products: Product[] = inventory.map((r, i) => ({
  sku: r.sku,
  name: r.name,
  upc: r.upc,
  seller: r.seller,
  category: CATEGORIES[i % 4] ?? "General",
  weightLb: WEIGHTS[i] ?? 1,
  active: i !== 7,
}));

export type Seller = {
  id: string;
  name: string;
  contact: string;
  skus: number;
  openOrders: number;
  warehouses: Warehouse[];
  status: "active" | "onboarding" | "paused";
};

export const sellers: Seller[] = [
  { id: "SEL-001", name: "Northgate Supply", contact: "ops@northgate.co", skus: 128, openOrders: 34, warehouses: ["RENO", "COLUMBUS"], status: "active" },
  { id: "SEL-002", name: "Cobalt Trading", contact: "fulfil@cobalt.io", skus: 76, openOrders: 21, warehouses: ["COLUMBUS"], status: "active" },
  { id: "SEL-003", name: "Harbor Line Goods", contact: "team@harborline.com", skus: 44, openOrders: 12, warehouses: ["RENO"], status: "onboarding" },
  { id: "SEL-004", name: "Verdant Home", contact: "logistics@verdant.com", skus: 19, openOrders: 0, warehouses: ["RENO", "COLUMBUS"], status: "paused" },
];

export type Receipt = {
  id: string;
  seller: string;
  warehouse: Warehouse;
  expected: number;
  received: number;
  status: "awaiting" | "in_progress" | "discrepancy" | "closed";
  arrived: string;
};

export const receipts: Receipt[] = [
  { id: "RCV-2201", seller: "Northgate Supply", warehouse: "RENO", expected: 480, received: 480, status: "closed", arrived: "07:15" },
  { id: "RCV-2202", seller: "Cobalt Trading", warehouse: "COLUMBUS", expected: 260, received: 244, status: "discrepancy", arrived: "08:02" },
  { id: "RCV-2203", seller: "Harbor Line Goods", warehouse: "RENO", expected: 120, received: 58, status: "in_progress", arrived: "09:30" },
  { id: "RCV-2204", seller: "Northgate Supply", warehouse: "COLUMBUS", expected: 900, received: 0, status: "awaiting", arrived: "—" },
  { id: "RCV-2205", seller: "Cobalt Trading", warehouse: "RENO", expected: 75, received: 61, status: "discrepancy", arrived: "10:11" },
];

export type AuditEvent = {
  id: string;
  time: string;
  action: string;
  subject: string;
  field?: string;
  from?: string;
  to?: string;
  warehouse?: Warehouse;
  user: string;
  role: string;
  kind: "inventory" | "reservation" | "receiving" | "order" | "auth" | "product";
  detail: string;
};

export const auditEvents: AuditEvent[] = [
  { id: "AUD-9001", time: "10:42 AM", action: "Inventory adjusted", subject: "Wireless Keyboard", field: "Available", from: "120", to: "130", warehouse: "RENO", user: "Rudra Dalal", role: "Manager", kind: "inventory", detail: "Cycle count correction against bin R-14-C. Delta +10 units applied atomically." },
  { id: "AUD-9002", time: "10:31 AM", action: "Reservation created", subject: "Order #ORD-10482", to: "5 units reserved", warehouse: "RENO", user: "A. Whitfield", role: "Operator", kind: "reservation", detail: "Atomic reservation across 2 lines. No oversell detected." },
  { id: "AUD-9003", time: "10:12 AM", action: "Receiving discrepancy", subject: "RCV-2202", field: "Received", from: "260", to: "244", warehouse: "COLUMBUS", user: "M. Torres", role: "Operator", kind: "receiving", detail: "16 units short on pallet 3. Flagged for seller reconciliation." },
  { id: "AUD-9004", time: "09:58 AM", action: "Order packed", subject: "Order #ORD-10485", from: "PICKING", to: "PACKED", warehouse: "COLUMBUS", user: "J. Baptiste", role: "Operator", kind: "order", detail: "9 lines, 48 units. Package weight 31.2 lb, carrier assigned." },
  { id: "AUD-9005", time: "09:34 AM", action: "Product updated", subject: "SKU-8842", field: "UPC", from: "017775678000", to: "017775678884", user: "Rudra Dalal", role: "Manager", kind: "product", detail: "UPC corrected after scan mismatch reported by Reno floor." },
  { id: "AUD-9006", time: "09:02 AM", action: "Role granted", subject: "M. Torres", field: "Role", from: "Viewer", to: "Operator", user: "Rudra Dalal", role: "Manager", kind: "auth", detail: "RBAC change. Scope limited to COLUMBUS warehouse." },
  { id: "AUD-9007", time: "08:47 AM", action: "Inventory adjusted", subject: "USB-C Hub 7-Port", field: "Available", from: "58", to: "42", warehouse: "RENO", user: "M. Torres", role: "Operator", kind: "inventory", detail: "Damage write-off, 16 units moved to quarantine." },
];

export type User = {
  name: string;
  email: string;
  role: "Admin" | "Manager" | "Operator" | "Viewer";
  warehouses: Warehouse[] | "ALL";
  lastActive: string;
  status: "active" | "invited" | "suspended";
};

export const users: User[] = [
  { name: "Rudra Dalal", email: "rudra@whitfield.co", role: "Admin", warehouses: "ALL", lastActive: "2 min ago", status: "active" },
  { name: "A. Whitfield", email: "avery@whitfield.co", role: "Manager", warehouses: ["RENO"], lastActive: "14 min ago", status: "active" },
  { name: "M. Torres", email: "m.torres@whitfield.co", role: "Operator", warehouses: ["COLUMBUS"], lastActive: "1 hr ago", status: "active" },
  { name: "J. Baptiste", email: "j.baptiste@whitfield.co", role: "Operator", warehouses: ["COLUMBUS"], lastActive: "3 hr ago", status: "active" },
  { name: "P. Nayar", email: "p.nayar@whitfield.co", role: "Viewer", warehouses: ["RENO", "COLUMBUS"], lastActive: "—", status: "invited" },
];

export const dashboard = {
  availableUnits: 12480,
  activeOrders: 342,
  needAttention: 18,
  attention: [
    { label: "7 low-stock products", to: "/inventory" },
    { label: "4 orders approaching SLA", to: "/fulfillment" },
    { label: "2 receiving discrepancies", to: "/receiving" },
  ],
  warehouses: [
    { name: "RENO" as Warehouse, available: 8421, reserved: 1104, orders: 214, utilisation: 0.72 },
    { name: "COLUMBUS" as Warehouse, available: 4059, reserved: 612, orders: 128, utilisation: 0.54 },
  ],
  throughput: [18, 24, 31, 29, 44, 52, 47, 61, 58, 72, 66, 81],
};
