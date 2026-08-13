/**
 * Auth API Module.
 * Wraps backend authentication endpoints: /v1/auth/login and /v1/auth/me.
 */

import { api } from "./client";
import { User } from "@/types/wms";

export interface LoginPayload {
  username: string; // Accepts email or username string
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function loginApi(credentials: LoginPayload): Promise<LoginResponse> {
  const body = {
    email: credentials.username,
    password: credentials.password,
  };
  return api.post<LoginResponse>("/v1/auth/login", body, { skipAuth: true });
}

export async function getCurrentUserApi(): Promise<User> {
  return api.get<User>("/v1/auth/me");
}
