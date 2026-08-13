import { describe, it, expect } from "vitest";
import { parseApiError, createNetworkError, WmsApiError } from "../errors";

describe("WMS Error System", () => {
  it("should format 401 unauthenticated errors", async () => {
    const mockResponse = new Response(JSON.stringify({ detail: "Could not validate credentials" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
    const err = await parseApiError(mockResponse);
    expect(err).toBeInstanceOf(WmsApiError);
    expect(err.status).toBe(401);
    expect(err.message).toBe("Could not validate credentials");
  });

  it("should format 422 field validation errors from Pydantic", async () => {
    const mockResponse = new Response(
      JSON.stringify({
        detail: [
          { loc: ["body", "email"], msg: "field required", type: "value_error.missing" },
          { loc: ["body", "password"], msg: "ensure this value has at least 8 characters" },
        ],
      }),
      { status: 422, headers: { "Content-Type": "application/json" } }
    );
    const err = await parseApiError(mockResponse);
    expect(err.status).toBe(422);
    expect(err.fieldErrors).toBeDefined();
    expect(err.fieldErrors?.length).toBe(2);
    expect(err.fieldErrors?.[0].field).toBe("email");
  });

  it("should format network error properly", () => {
    const netErr = createNetworkError(new Error("Failed to fetch"));
    expect(netErr.isNetworkError).toBe(true);
    expect(netErr.status).toBe(0);
    expect(netErr.code).toBe("NETWORK_ERROR");
  });
});
