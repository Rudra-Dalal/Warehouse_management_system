import { describe, it, expect, vi, beforeEach } from "vitest";
import { getOrdersApi, getOrderByIdApi, createOrderApi } from "../orders";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Orders API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch list of orders", async () => {
    const mockOrders = [
      { order_id: "ord-1", seller_id: "s1", warehouse_id: "RENO", customer_name: "Alice", shipping_address: "123 St", status: "CONFIRMED", items: [] },
    ];
    (api.get as any).mockResolvedValue(mockOrders);

    const result = await getOrdersApi();
    expect(api.get).toHaveBeenCalledWith("/v1/orders/");
    expect(result).toEqual(mockOrders);
  });

  it("should fetch order by ID", async () => {
    const mockOrder = { order_id: "ord-1", status: "CONFIRMED" };
    (api.get as any).mockResolvedValue(mockOrder);

    const result = await getOrderByIdApi("ord-1");
    expect(api.get).toHaveBeenCalledWith("/v1/orders/ord-1");
    expect(result).toEqual(mockOrder);
  });

  it("should create new customer order", async () => {
    const payload = {
      seller_id: "s1",
      warehouse_id: "COLUMBUS" as const,
      customer_name: "Bob",
      shipping_address: "456 Ave",
      items: [{ product_id: "p1", quantity: 2 }],
    };
    const mockRes = { order_id: "ord-2", ...payload, status: "CONFIRMED", created_at: "2026-08-13" };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await createOrderApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/orders/", payload);
    expect(result).toEqual(mockRes);
  });
});
