/**
 * Inventory API Module.
 */

import { api } from "./client";
import { Inventory, InventoryMovement, Reservation, WarehouseId } from "@/types/wms";

export interface GetInventoryParams {
  warehouse_id?: WarehouseId;
  product_id?: string;
  sku?: string;
}

export interface AdjustInventoryPayload {
  warehouse_id: WarehouseId;
  product_id: string;
  quantity_delta: number;
  reason?: string;
}

export interface ReserveInventoryPayload {
  order_id: string;
  warehouse_id: WarehouseId;
  product_id: string;
  quantity: number;
}

export interface GetMovementsParams {
  warehouse_id?: WarehouseId;
  product_id?: string;
  limit?: number;
}

export async function getInventoryApi(params?: GetInventoryParams): Promise<Inventory[]> {
  const queryParams = new URLSearchParams();
  if (params?.warehouse_id) queryParams.append("warehouse_id", params.warehouse_id);
  if (params?.product_id) queryParams.append("product_id", params.product_id);
  if (params?.sku) queryParams.append("sku", params.sku);

  const queryStr = queryParams.toString();
  const endpoint = `/v1/inventory/${queryStr ? `?${queryStr}` : ""}`;
  return api.get<Inventory[]>(endpoint);
}

export async function getInventoryItemApi(
  warehouseId: WarehouseId,
  productId: string
): Promise<Inventory> {
  return api.get<Inventory>(`/v1/inventory/${warehouseId}/${productId}`);
}

export async function adjustInventoryApi(payload: AdjustInventoryPayload): Promise<Inventory> {
  return api.post<Inventory>("/v1/inventory/adjust", payload);
}

export async function reserveInventoryApi(payload: ReserveInventoryPayload): Promise<Reservation> {
  return api.post<Reservation>("/v1/inventory/reserve", payload);
}

export async function getInventoryMovementsApi(
  params?: GetMovementsParams
): Promise<InventoryMovement[]> {
  const queryParams = new URLSearchParams();
  if (params?.warehouse_id) queryParams.append("warehouse_id", params.warehouse_id);
  if (params?.product_id) queryParams.append("product_id", params.product_id);
  if (params?.limit) queryParams.append("limit", params.limit.toString());

  const queryStr = queryParams.toString();
  const endpoint = `/v1/inventory/movements${queryStr ? `?${queryStr}` : ""}`;
  return api.get<InventoryMovement[]>(endpoint);
}
