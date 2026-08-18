/**
 * React Context Provider for Authentication and Session state.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, Permission, Role } from "@/types/wms";
import { sessionManager } from "./session";
import { loginApi, getCurrentUserApi, LoginPayload } from "@/api/auth";
import { hasPermission as checkPermission, hasRole as checkRole } from "./rbac";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  activeWarehouse: string | null;
  setActiveWarehouse: (wh: string) => void;
  login: (credentials: LoginPayload) => Promise<void>;
  logout: () => void;
  refetchUser: () => Promise<void>;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (roles: Role | Role[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const isBrowser = typeof window !== "undefined";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(sessionManager.getUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeWarehouse, setActiveWarehouseState] = useState<string | null>(
    isBrowser ? localStorage.getItem("activeWarehouse") || null : null,
  );

  const setActiveWarehouse = useCallback((wh: string) => {
    setActiveWarehouseState(wh);
    if (isBrowser) localStorage.setItem("activeWarehouse", wh);
  }, []);

  const initializeWarehouse = (fetchedUser: User) => {
    if (fetchedUser) {
      let defaultWh = isBrowser ? localStorage.getItem("activeWarehouse") : null;
      if (fetchedUser.role === "ADMIN") {
        if (!defaultWh) defaultWh = "RENO";
      } else {
        if (!defaultWh || !fetchedUser.assigned_warehouse_ids?.includes(defaultWh)) {
          defaultWh = fetchedUser.assigned_warehouse_ids?.[0] || null;
        }
      }
      if (defaultWh) {
        setActiveWarehouse(defaultWh);
      } else {
        setActiveWarehouseState(null);
        if (isBrowser) localStorage.removeItem("activeWarehouse");
      }
    }
  };

  const refetchUser = useCallback(async () => {
    const token = sessionManager.getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await getCurrentUserApi();
      setUser(currentUser);
      sessionManager.setSession(token, currentUser);
      initializeWarehouse(currentUser);
    } catch (err: any) {
      console.warn("Failed to validate active session on startup:", err);
      sessionManager.clearSession();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [setActiveWarehouse]);

  useEffect(() => {
    refetchUser();

    const unsubscribe = sessionManager.subscribe((session) => {
      setUser(session ? session.user : null);
      if (session?.user) {
        initializeWarehouse(session.user);
      }
    });

    return () => unsubscribe();
  }, [refetchUser]);

  const login = async (credentials: LoginPayload) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await loginApi(credentials);
      sessionManager.setSession(response.access_token, response.user || null);

      let loggedInUser = response.user;
      if (!loggedInUser) {
        loggedInUser = await getCurrentUserApi();
      }

      sessionManager.setSession(response.access_token, loggedInUser);
      setUser(loggedInUser);
      initializeWarehouse(loggedInUser);
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Check email and password.");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    sessionManager.clearSession();
    setUser(null);
    setActiveWarehouseState(null);
    if (isBrowser) localStorage.removeItem("activeWarehouse");
  };

  const hasPermission = (permission: Permission) => checkPermission(user, permission);
  const hasRole = (roles: Role | Role[]) => checkRole(user, roles);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        activeWarehouse,
        setActiveWarehouse,
        login,
        logout,
        refetchUser,
        hasPermission,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
