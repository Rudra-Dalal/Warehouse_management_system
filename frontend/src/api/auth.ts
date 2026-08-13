/**
 * Auth API Module.
 * Wraps backend authentication endpoints: /v1/auth/login and /v1/auth/me.
 */

import { api } from "./client";
import { User, Permission } from "@/types/wms";

export interface LoginPayload {
  username: string; // backend login expects username or email
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function loginApi(credentials: LoginPayload): Promise<LoginResponse> {
  return api.post<LoginResponse>("/v1/auth/login", credentials, { skipAuth: true });
}

export async function getCurrentUserApi(): Promise<User> {
  return api.get<User>("/v1/auth/me");
}
