/**
 * Receiving API Module.
 */

import { api } from "./client";
import { ReceivingRecord, ReceivingItem, WarehouseId } from "@/types/wms";

export interface CreateReceivingPayload {
  seller_id: string;
  warehouse_id: WarehouseId;
  items: ReceivingItem[];
  notes?: string;
}

export async function getReceivingRecordsApi(): Promise<ReceivingRecord[]> {
  return api.get<ReceivingRecord[]>("/v1/receiving/");
}

export async function getReceivingRecordByIdApi(receivingId: string): Promise<ReceivingRecord> {
  return api.get<ReceivingRecord>(`/v1/receiving/${receivingId}`);
}

export async function createReceivingRecordApi(
  payload: CreateReceivingPayload
): Promise<ReceivingRecord> {
  return api.post<ReceivingRecord>("/v1/receiving/", payload);
}
