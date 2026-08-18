/**
 * Orders API Module.
 */

import { api } from "./client";
import { Order, OrderItem, WarehouseId } from "@/types/wms";

export interface CreateOrderPayload {
  seller_id: string;
  warehouse_id: WarehouseId;
  customer_name: string;
  shipping_address: string;
  items: OrderItem[];
}

export async function getOrdersApi(warehouse_code?: string): Promise<Order[]> {
  const queryParams = new URLSearchParams();
  if (warehouse_code) queryParams.append("warehouse_code", warehouse_code);
  const queryStr = queryParams.toString();
  return api.get<Order[]>(`/v1/orders/${queryStr ? `?${queryStr}` : ""}`);
}

export async function getOrderByIdApi(orderId: string): Promise<Order> {
  return api.get<Order>(`/v1/orders/${orderId}`);
}

export async function createOrderApi(payload: CreateOrderPayload): Promise<Order> {
  return api.post<Order>("/v1/orders/", payload);
}
