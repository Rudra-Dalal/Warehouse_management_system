/**
 * Natural Language Voice Command Parser & Entity Resolution.
 * Maps raw transcripts into strongly-typed WMS Voice Commands.
 */

import { WarehouseId, OrderStatus } from "@/types/wms";

export type VoiceIntent =
  | "inventory_lookup"
  | "product_lookup"
  | "order_lookup"
  | "fulfillment_lookup"
  | "audit_lookup"
  | "dashboard_lookup"
  | "adjust_inventory"
  | "reserve_inventory"
  | "receive_inventory"
  | "unknown";


export interface ParsedEntities {
  sku?: string;
  upc?: string;
  productQuery?: string;
  warehouse_id?: WarehouseId;
  order_id?: string;
  quantity?: number;
  stage?: OrderStatus;
}

export interface VoiceCommand {
  intent: VoiceIntent;
  entities: ParsedEntities;
  isMutating: boolean;
  originalTranscript: string;
  confidence: number;
  clarificationNeeded?: string;
}

export function parseVoiceCommand(transcript: string, confidence = 0.95): VoiceCommand {
  const text = transcript.trim().toLowerCase();
  const rawText = transcript.trim();

  const entities: ParsedEntities = {};

  // Extract Warehouse
  if (text.includes("reno")) {
    entities.warehouse_id = "RENO";
  } else if (text.includes("columbus")) {
    entities.warehouse_id = "COLUMBUS";
  }

  // Extract SKU (e.g., "sku-1048", "sku 1048", or "sku1048")
  const skuMatch = rawText.match(/sku[-:\s]?([a-z0-9]+)/i);
  if (skuMatch) {
    entities.sku = `SKU-${skuMatch[1].toUpperCase().replace(/^SKU-?/, "")}`;
  }

  // Extract UPC (e.g., 10-12 digits)
  const upcMatch = text.match(/\b\d{10,12}\b/);
  if (upcMatch) {
    entities.upc = upcMatch[0].padStart(12, "0");
  }

  // Extract Order ID (e.g. "ord-1001", "order 1001", "order ORD-1001")
  const orderMatch = rawText.match(/(?:order|ord)[-:\s]?([a-z0-9-]+)/i);
  if (orderMatch) {
    const val = orderMatch[1].toUpperCase();
    entities.order_id = val.startsWith("ORD-") ? val : `ORD-${val}`;
  }

  // Extract Quantity (e.g., "by 10", "5 units", "quantity 20")
  const qtyMatch = text.match(/(?:by|quantity|reserve|add|count|minus|plus|\+|-)\s*(-?\d+)/);
  if (qtyMatch) {
    entities.quantity = parseInt(qtyMatch[1], 10);
  } else {
    // Fallback digit match
    const numMatch = text.match(/\b(\d+)\s*(?:units|items|pcs|pieces)?\b/);
    if (numMatch && !entities.upc && !entities.order_id?.includes(numMatch[1])) {
      entities.quantity = parseInt(numMatch[1], 10);
    }
  }

  // Determine Intent

  // 1. Mutating: Adjust Inventory
  if (
    text.includes("adjust inventory") ||
    text.includes("adjust stock") ||
    text.includes("increase stock") ||
    text.includes("decrease stock") ||
    text.includes("add stock")
  ) {
    if (!entities.sku && !entities.upc) {
      return {
        intent: "adjust_inventory",
        entities,
        isMutating: true,
        originalTranscript: rawText,
        confidence,
        clarificationNeeded: "Please specify a product SKU or UPC to adjust stock.",
      };
    }
    if (entities.quantity === undefined) {
      return {
        intent: "adjust_inventory",
        entities,
        isMutating: true,
        originalTranscript: rawText,
        confidence,
        clarificationNeeded: "Please specify the quantity delta (e.g., by 10 or -5).",
      };
    }

    return {
      intent: "adjust_inventory",
      entities,
      isMutating: true,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 2. Mutating: Reserve Inventory
  if (text.includes("reserve") || text.includes("reservation")) {
    if (!entities.order_id) {
      return {
        intent: "reserve_inventory",
        entities,
        isMutating: true,
        originalTranscript: rawText,
        confidence,
        clarificationNeeded: "Which order ID would you like to reserve stock for?",
      };
    }

    return {
      intent: "reserve_inventory",
      entities,
      isMutating: true,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 3. Mutating: Receive Inventory
  if (
    text.includes("receive") ||
    text.includes("inbound") ||
    text.includes("log receipt") ||
    text.includes("dock receipt")
  ) {
    if (!entities.sku && !entities.upc) {
      return {
        intent: "receive_inventory",
        entities,
        isMutating: true,
        originalTranscript: rawText,
        confidence,
        clarificationNeeded: "Please specify the product SKU or UPC to receive.",
      };
    }
    if (entities.quantity === undefined || entities.quantity <= 0) {
      return {
        intent: "receive_inventory",
        entities,
        isMutating: true,
        originalTranscript: rawText,
        confidence,
        clarificationNeeded: "Please state the quantity of units received.",
      };
    }

    return {
      intent: "receive_inventory",
      entities,
      isMutating: true,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 4. Read: Fulfillment Lookup
  if (
    text.includes("fulfillment") ||
    text.includes("ready to pack") ||
    text.includes("waiting to ship") ||
    text.includes("picking queue") ||
    text.includes("packed") ||
    text.includes("shipped")
  ) {
    if (text.includes("pack")) entities.stage = "PACKED";
    else if (text.includes("ship")) entities.stage = "SHIPPED";
    else if (text.includes("pick")) entities.stage = "PICKING";

    return {
      intent: "fulfillment_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 4. Read: Order Lookup
  if (text.includes("order") || text.includes("order status")) {
    return {
      intent: "order_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 5. Read: Audit Lookup
  if (text.includes("audit") || text.includes("history") || text.includes("activity log")) {
    return {
      intent: "audit_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 6. Read: Product Lookup
  if (text.includes("find product") || text.includes("look up") || text.includes("product")) {
    return {
      intent: "product_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 7. Read: Inventory / Stock Lookup
  if (
    text.includes("inventory") ||
    text.includes("stock") ||
    text.includes("available") ||
    text.includes("how many") ||
    entities.sku ||
    entities.upc
  ) {
    return {
      intent: "inventory_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // 8. Read: Dashboard Overview
  if (
    text.includes("dashboard") ||
    text.includes("overview") ||
    text.includes("active orders") ||
    text.includes("summary")
  ) {
    return {
      intent: "dashboard_lookup",
      entities,
      isMutating: false,
      originalTranscript: rawText,
      confidence,
    };
  }

  // Fallback: Unknown Intent
  return {
    intent: "unknown",
    entities,
    isMutating: false,
    originalTranscript: rawText,
    confidence,
    clarificationNeeded: "Could not identify a supported WMS command. Try 'Show inventory for SKU 1048' or 'What orders are ready to pack?'.",
  };
}
