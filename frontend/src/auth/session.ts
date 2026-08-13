/**
 * Session storage abstraction for storing JWT tokens and active user identity.
 * Components/API clients must rely on this module rather than touching localStorage directly.
 */

const TOKEN_KEY = "whitfield_wms_jwt_token";
const USER_KEY = "whitfield_wms_user_data";

export interface StoredSession {
  token: string;
  user: any;
}

type SessionChangeListener = (session: StoredSession | null) => void;
const listeners: Set<SessionChangeListener> = new Set();

export const sessionManager = {
  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  getUser(): any | null {
    if (typeof window === "undefined") return null;
    const data = localStorage.getItem(USER_KEY);
    if (!data) return null;
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  },

  setSession(token: string, user: any): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    const session = { token, user };
    listeners.forEach((listener) => listener(session));
  },

  clearSession(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    listeners.forEach((listener) => listener(null));
  },

  subscribe(listener: SessionChangeListener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
