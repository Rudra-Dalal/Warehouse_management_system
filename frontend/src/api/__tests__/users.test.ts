import { describe, it, expect, vi, beforeEach } from "vitest";
import { getUsersApi, getUserByIdApi, createUserApi, updateUserApi } from "../users";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

describe("Users API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch list of users", async () => {
    const mockUsers = [
      { user_id: "u1", username: "admin", email: "admin@wms.com", role: "ADMIN", is_active: true },
    ];
    (api.get as any).mockResolvedValue(mockUsers);

    const result = await getUsersApi();
    expect(api.get).toHaveBeenCalledWith("/v1/users");
    expect(result).toEqual(mockUsers);
  });

  it("should fetch user by ID", async () => {
    const mockUser = { user_id: "u1", username: "admin" };
    (api.get as any).mockResolvedValue(mockUser);

    const result = await getUserByIdApi("u1");
    expect(api.get).toHaveBeenCalledWith("/v1/users/u1");
    expect(result).toEqual(mockUser);
  });

  it("should create user account", async () => {
    const payload = {
      username: "operator1",
      email: "op@wms.com",
      full_name: "Operator One",
      password: "SecretPassword123!",
      role: "INVENTORY_CLERK" as const,
    };
    const mockRes = { user_id: "u2", ...payload, is_active: true };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await createUserApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/users", payload);
    expect(result).toEqual(mockRes);
  });

  it("should update user profile or role", async () => {
    const payload = { role: "WAREHOUSE_MANAGER" as const };
    const mockRes = { user_id: "u2", role: "WAREHOUSE_MANAGER" };
    (api.patch as any).mockResolvedValue(mockRes);

    const result = await updateUserApi("u2", payload);
    expect(api.patch).toHaveBeenCalledWith("/v1/users/u2", payload);
    expect(result).toEqual(mockRes);
  });
});
