import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // undefined = checking, null = not authenticated, object = authenticated
  const [user, setUser] = useState(undefined);

  const checkAuth = useCallback(async () => {
    const previewRoute =
      import.meta.env.DEV &&
      ["/app/mindguard", "/app/health-reserve"].includes(window.location.pathname) &&
      new URLSearchParams(window.location.search).get("preview") === "1";
    if (previewRoute) {
      setUser(null);
      return;
    }

    try {
      const { data } = await api.get("/auth/me/");
      setUser(data);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, checkAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
