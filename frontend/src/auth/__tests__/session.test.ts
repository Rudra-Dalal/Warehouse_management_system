import { describe, it, expect, beforeEach, vi } from "vitest";
import { sessionManager } from "../session";

// In-memory localStorage mock for node test environment
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(globalThis, "window", {
  value: { localStorage: localStorageMock },
  writable: true,
});
Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  writable: true,
});

describe("Session Manager Storage Abstraction", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should return null when no token or user exists", () => {
    expect(sessionManager.getToken()).toBeNull();
    expect(sessionManager.getUser()).toBeNull();
  });

  it("should set and retrieve session token and user", () => {
    const dummyUser = { user_id: "u123", username: "testuser", role: "ADMIN" };
    sessionManager.setSession("jwt_token_123", dummyUser);

    expect(sessionManager.getToken()).toBe("jwt_token_123");
    expect(sessionManager.getUser()).toEqual(dummyUser);
  });

  it("should notify subscribers when session changes", () => {
    const listener = vi.fn();
    const unsubscribe = sessionManager.subscribe(listener);

    const dummyUser = { user_id: "u123", username: "testuser" };
    sessionManager.setSession("token_abc", dummyUser);

    expect(listener).toHaveBeenCalledWith({ token: "token_abc", user: dummyUser });

    sessionManager.clearSession();
    expect(listener).toHaveBeenCalledWith(null);

    unsubscribe();
  });

  it("should clear session properly", () => {
    sessionManager.setSession("token_xyz", { username: "user" });
    expect(sessionManager.getToken()).toBe("token_xyz");

    sessionManager.clearSession();
    expect(sessionManager.getToken()).toBeNull();
    expect(sessionManager.getUser()).toBeNull();
  });
});
