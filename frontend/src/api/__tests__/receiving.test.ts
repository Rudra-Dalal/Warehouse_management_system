import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getReceivingRecordsApi,
  getReceivingRecordByIdApi,
  createReceivingRecordApi,
} from "../receiving";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Receiving API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch receiving records", async () => {
    const mockRecs = [
      {
        receiving_id: "rec1",
        seller_id: "s1",
        warehouse_id: "RENO",
        status: "COMPLETED",
        items: [],
        received_by: "u1",
        received_at: "2026-08-13T10:00:00Z",
      },
    ];
    (api.get as any).mockResolvedValue(mockRecs);

    const result = await getReceivingRecordsApi();
    expect(api.get).toHaveBeenCalledWith("/v1/receiving/");
    expect(result).toEqual(mockRecs);
  });

  it("should fetch receiving record by ID", async () => {
    const mockRec = { receiving_id: "rec1", status: "COMPLETED" };
    (api.get as any).mockResolvedValue(mockRec);

    const result = await getReceivingRecordByIdApi("rec1");
    expect(api.get).toHaveBeenCalledWith("/v1/receiving/rec1");
    expect(result).toEqual(mockRec);
  });

  it("should log inbound receipt", async () => {
    const payload = {
      seller_id: "s1",
      warehouse_id: "RENO" as const,
      items: [{ product_id: "p1", quantity_received: 100 }],
      notes: "Pallet 1",
    };
    const mockRes = {
      receiving_id: "rec2",
      ...payload,
      status: "COMPLETED",
      received_by: "u1",
      received_at: "2026-08-13",
    };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await createReceivingRecordApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/receiving/", payload);
    expect(result).toEqual(mockRes);
  });
});
