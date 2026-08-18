import { describe, it, expect, vi, beforeEach } from "vitest";
import { getSellersApi, getSellerByIdApi, createSellerApi } from "../sellers";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Sellers API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch list of sellers", async () => {
    const mockSellers = [
      {
        seller_id: "s1",
        name: "Northgate Supply",
        code: "NGS",
        contact_email: "contact@ngs.com",
        is_active: true,
      },
    ];
    (api.get as any).mockResolvedValue(mockSellers);

    const result = await getSellersApi();
    expect(api.get).toHaveBeenCalledWith("/v1/sellers/");
    expect(result).toEqual(mockSellers);
  });

  it("should fetch seller by ID", async () => {
    const mockSeller = { seller_id: "s1", name: "Northgate Supply" };
    (api.get as any).mockResolvedValue(mockSeller);

    const result = await getSellerByIdApi("s1");
    expect(api.get).toHaveBeenCalledWith("/v1/sellers/s1");
    expect(result).toEqual(mockSeller);
  });

  it("should create new seller", async () => {
    const payload = { name: "Cobalt Trading", code: "CBLT", contact_email: "info@cobalt.com" };
    const mockRes = { seller_id: "s2", ...payload, is_active: true };
    (api.post as any).mockResolvedValue(mockRes);

    const result = await createSellerApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/sellers/", payload);
    expect(result).toEqual(mockRes);
  });
});
