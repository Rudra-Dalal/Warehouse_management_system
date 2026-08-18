/**
 * Central HTTP Client for WMS Frontend.
 * Features:
 * - Environment base URL configuration
 * - Automatic Authorization Header injection
 * - Request/Response JSON serialization
 * - Normalized Error Handling
 * - Timeout support
 * - Automatic 401 clearing
 */

import { sessionManager } from "@/auth/session";
import { createNetworkError, parseApiError, WmsApiError } from "./errors";

const BASE_URL = (
  (import.meta.env as Record<string, string | undefined>)["VITE_API_BASE_URL"] ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  skipAuth?: boolean;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const {
    timeoutMs = 15000,
    skipAuth = false,
    headers: customHeaders,
    body,
    ...customOptions
  } = options;

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = sessionManager.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    const fetchInit: RequestInit = {
      ...customOptions,
      headers,
      signal: controller.signal,
    };
    if (body !== undefined && body !== null) {
      fetchInit.body = typeof body === "string" ? body : JSON.stringify(body);
    }
    response = await fetch(url, fetchInit);
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new WmsApiError({
        status: 0,
        message: "Request timed out. Please try again.",
        code: "TIMEOUT_ERROR",
        isNetworkError: true,
      });
    }
    throw createNetworkError(err);
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    if (response.status === 401) {
      sessionManager.clearSession();
    }
    const error = await parseApiError(response);
    throw error;
  }

  // Check 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

export const api = {
  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return apiClient<T>(endpoint, { ...options, method: "GET" });
  },

  post<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiClient<T>(endpoint, { ...options, method: "POST", body });
  },

  put<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiClient<T>(endpoint, { ...options, method: "PUT", body });
  },

  patch<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiClient<T>(endpoint, { ...options, method: "PATCH", body });
  },

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return apiClient<T>(endpoint, { ...options, method: "DELETE" });
  },
};
