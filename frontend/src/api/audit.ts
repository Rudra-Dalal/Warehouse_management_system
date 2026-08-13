/**
 * Audit API Module.
 */

import { api } from "./client";
import { AuditLog, WarehouseId } from "@/types/wms";

export interface GetAuditLogsParams {
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  warehouse_id?: WarehouseId;
  action?: string;
  limit?: number;
}

export async function getAuditLogsApi(params?: GetAuditLogsParams): Promise<AuditLog[]> {
  const queryParams = new URLSearchParams();
  if (params?.entity_type) queryParams.append("entity_type", params.entity_type);
  if (params?.entity_id) queryParams.append("entity_id", params.entity_id);
  if (params?.user_id) queryParams.append("user_id", params.user_id);
  if (params?.warehouse_id) queryParams.append("warehouse_id", params.warehouse_id);
  if (params?.action) queryParams.append("action", params.action);
  if (params?.limit) queryParams.append("limit", params.limit.toString());

  const queryStr = queryParams.toString();
  const endpoint = `/v1/audit/logs${queryStr ? `?${queryStr}` : ""}`;
  return api.get<AuditLog[]>(endpoint);
}
