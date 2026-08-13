/**
 * Users API Module.
 */

import { api } from "./client";
import { User, Role } from "@/types/wms";

export interface CreateUserPayload {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: Role;
}

export interface UpdateUserPayload {
  full_name?: string;
  email?: string;
  role?: Role;
  is_active?: boolean;
}

export async function getUsersApi(): Promise<User[]> {
  return api.get<User[]>("/v1/users");
}

export async function getUserByIdApi(userId: string): Promise<User> {
  return api.get<User>(`/v1/users/${userId}`);
}

export async function createUserApi(payload: CreateUserPayload): Promise<User> {
  return api.post<User>("/v1/users", payload);
}

export async function updateUserApi(userId: string, payload: UpdateUserPayload): Promise<User> {
  return api.patch<User>(`/v1/users/${userId}`, payload);
}
