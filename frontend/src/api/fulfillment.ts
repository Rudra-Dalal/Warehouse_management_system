/**
 * Fulfillment API Module.
 */

import { api } from "./client";
import { FulfillmentRecord, WarehouseId } from "@/types/wms";

export interface FulfillmentActionPayload {
  order_id: string;
  warehouse_id: WarehouseId;
  notes?: string;
}

export async function pickOrderApi(payload: FulfillmentActionPayload): Promise<FulfillmentRecord> {
  return api.post<FulfillmentRecord>("/v1/fulfillment/pick", payload);
}

export async function packOrderApi(payload: FulfillmentActionPayload): Promise<FulfillmentRecord> {
  return api.post<FulfillmentRecord>("/v1/fulfillment/pack", payload);
}

export async function shipOrderApi(payload: FulfillmentActionPayload): Promise<FulfillmentRecord> {
  return api.post<FulfillmentRecord>("/v1/fulfillment/ship", payload);
}

export async function getFulfillmentHistoryApi(orderId: string): Promise<FulfillmentRecord[]> {
  return api.get<FulfillmentRecord[]>(`/v1/fulfillment/orders/${orderId}`);
}
