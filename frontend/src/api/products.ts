/**
 * Products API Module.
 */

import { api } from "./client";
import { Product } from "@/types/wms";

export interface CreateProductPayload {
  sku: string;
  name: string;
  upc: string;
  seller_id: string;
  description?: string;
  reorder_point?: number;
}

export async function getProductsApi(): Promise<Product[]> {
  return api.get<Product[]>("/v1/products/");
}

export async function getProductByIdApi(productId: string): Promise<Product> {
  return api.get<Product>(`/v1/products/${productId}`);
}

export async function getProductBySkuApi(sku: string): Promise<Product> {
  return api.get<Product>(`/v1/products/sku/${sku}`);
}

export async function getProductByUpcApi(upc: string): Promise<Product> {
  return api.get<Product>(`/v1/products/upc/${upc}`);
}

export async function createProductApi(payload: CreateProductPayload): Promise<Product> {
  return api.post<Product>("/v1/products/", payload);
}
