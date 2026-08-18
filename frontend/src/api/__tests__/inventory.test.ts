import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getInventoryApi,
  adjustInventoryApi,
  reserveInventoryApi,
  getInventoryMovementsApi,
} from "../inventory";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Inventory API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch inventory list with query parameters", async () => {
    const mockInv = [
      {
        inventory_id: "inv1",
        warehouse_id: "RENO",
        product_id: "p1",
        quantity_available: 100,
        quantity_reserved: 10,
      },
    ];
    (api.get as any).mockResolvedValue(mockInv);

    const result = await getInventoryApi({ warehouse_id: "RENO", product_id: "p1" });
    expect(api.get).toHaveBeenCalledWith("/v1/inventory/?warehouse_id=RENO&product_id=p1");
    expect(result).toEqual(mockInv);
  });

  it("should post stock adjustment", async () => {
    const payload = {
      warehouse_id: "RENO" as const,
      product_id: "p1",
      quantity_delta: 25,
      reason: "Cycle count",
    };
    const mockRes = { inventory_id: "inv1", quantity_available: 125, quantity_reserved: 10 };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await adjustInventoryApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/inventory/adjust", payload);
    expect(result).toEqual(mockRes);
  });

  it("should post stock reservation", async () => {
    const payload = {
      order_id: "ord-1",
      warehouse_id: "COLUMBUS" as const,
      product_id: "p2",
      quantity: 5,
    };
    const mockRes = { reservation_id: "res1", ...payload, status: "ACTIVE" };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await reserveInventoryApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/inventory/reserve", payload);
    expect(result).toEqual(mockRes);
  });

  it("should fetch inventory movement history", async () => {
    const mockMovements = [
      {
        movement_id: "m1",
        warehouse_id: "RENO",
        product_id: "p1",
        movement_type: "ADJUSTMENT",
        quantity_delta: 10,
      },
    ];
    (api.get as any).mockResolvedValue(mockMovements);

    const result = await getInventoryMovementsApi({ warehouse_id: "RENO", limit: 20 });
    expect(api.get).toHaveBeenCalledWith("/v1/inventory/movements?warehouse_id=RENO&limit=20");
    expect(result).toEqual(mockMovements);
  });
});
