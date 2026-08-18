import { describe, it, expect, vi, beforeEach } from "vitest";
import { pickOrderApi, packOrderApi, shipOrderApi, getFulfillmentHistoryApi } from "../fulfillment";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Fulfillment API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should post pick order request", async () => {
    const payload = {
      order_id: "ord-1",
      warehouse_id: "RENO" as const,
      notes: "Picked from Bin A2",
    };
    const mockRes = { fulfillment_id: "f1", ...payload, action: "PICK" };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await pickOrderApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/fulfillment/pick", payload);
    expect(result).toEqual(mockRes);
  });

  it("should post pack order request", async () => {
    const payload = { order_id: "ord-1", warehouse_id: "RENO" as const };
    const mockRes = { fulfillment_id: "f2", ...payload, action: "PACK" };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await packOrderApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/fulfillment/pack", payload);
    expect(result).toEqual(mockRes);
  });

  it("should post ship order request", async () => {
    const payload = { order_id: "ord-1", warehouse_id: "RENO" as const };
    const mockRes = { fulfillment_id: "f3", ...payload, action: "SHIP" };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await shipOrderApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/fulfillment/ship", payload);
    expect(result).toEqual(mockRes);
  });

  it("should fetch fulfillment history for order", async () => {
    const mockHistory = [
      { fulfillment_id: "f1", action: "PICK" },
      { fulfillment_id: "f2", action: "PACK" },
    ];
    (api.get as any).mockResolvedValue(mockHistory);

    const result = await getFulfillmentHistoryApi("ord-1");
    expect(api.get).toHaveBeenCalledWith("/v1/fulfillment/orders/ord-1");
    expect(result).toEqual(mockHistory);
  });
});
