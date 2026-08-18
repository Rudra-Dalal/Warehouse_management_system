import { describe, it, expect, vi, beforeEach } from "vitest";
import { getAuditLogsApi } from "../audit";
import { api } from "../client";

vi.mock("../client", () => ({
  api: {
    get: vi.fn(),
  },
}));

describe("Audit API Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch audit logs with filters", async () => {
    const mockLogs = [
      {
        audit_id: "a1",
        entity_type: "INVENTORY",
        entity_id: "inv1",
        action: "ADJUST_STOCK",
        user_id: "u1",
        timestamp: "2026-08-13",
      },
    ];
    (api.get as any).mockResolvedValue(mockLogs);

    const result = await getAuditLogsApi({ entity_type: "INVENTORY", limit: 50 });
    expect(api.get).toHaveBeenCalledWith("/v1/audit/logs?entity_type=INVENTORY&limit=50");
    expect(result).toEqual(mockLogs);
  });
});
