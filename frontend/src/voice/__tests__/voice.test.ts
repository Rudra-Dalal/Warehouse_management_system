import { describe, it, expect, vi, beforeEach } from "vitest";
import { parseVoiceCommand } from "../command-parser";
import { VoiceController } from "../voice-controller";
import {
  SpeechToTextProvider,
  STTState,
  STTStateCallback,
  STTResultCallback,
  STTErrorCallback,
} from "../stt/provider";
import { User } from "@/types/wms";

// Mock STT Provider
class MockSTTProvider implements SpeechToTextProvider {
  private state: STTState = "idle";
  private transcript = "";

  private stateCBs: Set<STTStateCallback> = new Set();
  private resultCBs: Set<STTResultCallback> = new Set();
  private errorCBs: Set<STTErrorCallback> = new Set();

  isSupported() {
    return true;
  }
  getState() {
    return this.state;
  }
  async start() {
    this.state = "listening";
    this.stateCBs.forEach((fn) => fn("listening"));
  }
  async stop() {
    this.state = "success";
    this.stateCBs.forEach((fn) => fn("success"));
    return this.transcript;
  }
  cancel() {
    this.state = "cancelled";
    this.stateCBs.forEach((fn) => fn("cancelled"));
  }
  onStateChange(cb: STTStateCallback) {
    this.stateCBs.add(cb);
    return () => this.stateCBs.delete(cb);
  }
  onTranscript(cb: STTResultCallback) {
    this.resultCBs.add(cb);
    return () => this.resultCBs.delete(cb);
  }
  onError(cb: STTErrorCallback) {
    this.errorCBs.add(cb);
    return () => this.errorCBs.delete(cb);
  }

  // Helper for tests
  emitTranscript(text: string) {
    this.transcript = text;
    this.resultCBs.forEach((fn) => fn({ transcript: text, confidence: 0.98 }));
  }
}

const adminUser: User = {
  user_id: "u1",
  username: "admin",
  email: "admin@wms.com",
  full_name: "Admin User",
  role: "ADMIN",
  assigned_warehouse_ids: ["RENO", "COLUMBUS"],
  is_active: true,
};

const readOnlyUser: User = {
  user_id: "u2",
  username: "readonly",
  email: "read@wms.com",
  full_name: "Read Only",
  role: "READ_ONLY",
  assigned_warehouse_ids: ["RENO"],
  is_active: true,
};

describe("Voice Command Parser", () => {
  it("should parse inventory lookup for SKU and warehouse", () => {
    const cmd = parseVoiceCommand("Show inventory for SKU 1048 in Reno");
    expect(cmd.intent).toBe("inventory_lookup");
    expect(cmd.entities.sku).toBe("SKU-1048");
    expect(cmd.entities.warehouse_id).toBe("RENO");
    expect(cmd.isMutating).toBe(false);
  });

  it("should parse product lookup with UPC", () => {
    const cmd = parseVoiceCommand("Look up UPC 012345678905");
    expect(cmd.intent).toBe("product_lookup");
    expect(cmd.entities.upc).toBe("012345678905");
    expect(cmd.isMutating).toBe(false);
  });

  it("should parse order lookup", () => {
    const cmd = parseVoiceCommand("What is the status of order ORD-1001?");
    expect(cmd.intent).toBe("order_lookup");
    expect(cmd.entities.order_id).toBe("ORD-1001");
    expect(cmd.isMutating).toBe(false);
  });

  it("should parse fulfillment lookup for packing queue", () => {
    const cmd = parseVoiceCommand("What orders are ready to pack?");
    expect(cmd.intent).toBe("fulfillment_lookup");
    expect(cmd.entities.stage).toBe("PACKED");
    expect(cmd.isMutating).toBe(false);
  });

  it("should parse mutating inventory adjustment command", () => {
    const cmd = parseVoiceCommand("Adjust inventory for SKU 1048 by 10 in Reno");
    expect(cmd.intent).toBe("adjust_inventory");
    expect(cmd.entities.sku).toBe("SKU-1048");
    expect(cmd.entities.quantity).toBe(10);
    expect(cmd.entities.warehouse_id).toBe("RENO");
    expect(cmd.isMutating).toBe(true);
  });

  it("should request clarification for ambiguous adjustment command missing SKU", () => {
    const cmd = parseVoiceCommand("Adjust inventory by 5");
    expect(cmd.intent).toBe("adjust_inventory");
    expect(cmd.clarificationNeeded).toBeDefined();
  });
});

describe("Voice Controller Execution & RBAC", () => {
  let provider: MockSTTProvider;
  let controller: VoiceController;

  beforeEach(() => {
    provider = new MockSTTProvider();
    controller = new VoiceController(provider);
  });

  it("should require confirmation for mutating commands", async () => {
    await controller.startListening();
    provider.emitTranscript("Adjust inventory for SKU 1048 by 10");

    const cmd = await controller.stopAndProcess(adminUser);
    expect(cmd?.isMutating).toBe(true);

    const state = controller.getState();
    expect(state.pendingConfirmation).not.toBeNull();
    expect(state.pendingConfirmation?.intent).toBe("adjust_inventory");
  });

  it("should enforce RBAC permissions and deny mutating command for READ_ONLY user", async () => {
    await controller.startListening();
    provider.emitTranscript("Adjust inventory for SKU 1048 by 10");

    await controller.stopAndProcess(readOnlyUser);
    const state = controller.getState();

    expect(state.pendingConfirmation).toBeNull();
    expect(state.error).toContain("Permission denied");
  });
});
