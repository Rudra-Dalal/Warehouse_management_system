import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getProductsApi,
  getProductBySkuApi,
  getProductByUpcApi,
  createProductApi,
} from "../products";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Products API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch list of products", async () => {
    const mockProducts = [
      {
        product_id: "p1",
        sku: "SKU-100",
        name: "Keyboard",
        upc: "012345678905",
        seller_id: "s1",
        reorder_point: 50,
        is_active: true,
      },
    ];
    (api.get as any).mockResolvedValue(mockProducts);

    const result = await getProductsApi();
    expect(api.get).toHaveBeenCalledWith("/v1/products/");
    expect(result).toEqual(mockProducts);
  });

  it("should fetch product by SKU", async () => {
    const mockProduct = { product_id: "p1", sku: "SKU-100", name: "Keyboard" };
    (api.get as any).mockResolvedValue(mockProduct);

    const result = await getProductBySkuApi("SKU-100");
    expect(api.get).toHaveBeenCalledWith("/v1/products/sku/SKU-100");
    expect(result).toEqual(mockProduct);
  });

  it("should fetch product by UPC", async () => {
    const mockProduct = { product_id: "p1", upc: "012345678905", name: "Keyboard" };
    (api.get as any).mockResolvedValue(mockProduct);

    const result = await getProductByUpcApi("012345678905");
    expect(api.get).toHaveBeenCalledWith("/v1/products/upc/012345678905");
    expect(result).toEqual(mockProduct);
  });

  it("should create new product", async () => {
    const payload = {
      sku: "SKU-200",
      name: "Mouse",
      upc: "099988877766",
      seller_id: "s1",
      reorder_point: 25,
    };
    const mockResponse = { product_id: "p2", ...payload, is_active: true };
    (api.post as any).mockResolvedValue(mockResponse);

    const result = await createProductApi(payload);
    expect(api.post).toHaveBeenCalledWith("/v1/products/", payload);
    expect(result).toEqual(mockResponse);
  });
});
