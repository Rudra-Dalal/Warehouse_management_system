/**
 * Sellers API Module.
 */

import { api } from "./client";
import { Seller } from "@/types/wms";

export interface CreateSellerPayload {
  name: string;
  code: string;
  contact_email: string;
}

export async function getSellersApi(): Promise<Seller[]> {
  return api.get<Seller[]>("/v1/sellers/");
}

export async function getSellerByIdApi(sellerId: string): Promise<Seller> {
  return api.get<Seller>(`/v1/sellers/${sellerId}`);
}

export async function createSellerApi(payload: CreateSellerPayload): Promise<Seller> {
  return api.post<Seller>("/v1/sellers/", payload);
}
