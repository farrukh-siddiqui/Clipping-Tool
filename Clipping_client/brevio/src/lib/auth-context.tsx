"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api, type UserResponse, ApiError } from "@/lib/api";

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (
    email: string,
    password: string,
    redirectTo?: string | null,
  ) => Promise<void>;
  signup: (
    email: string,
    password: string,
    redirectTo?: string | null,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "brevio_token";

/** Max age aligns with typical JWT session (24h); proxy only needs the cookie present. */
const TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24;

function setAuthCookie(token: string) {
  const value = encodeURIComponent(token);
  document.cookie = `${TOKEN_KEY}=${value}; Path=/; Max-Age=${TOKEN_COOKIE_MAX_AGE}; SameSite=Lax`;
}

function clearAuthCookie() {
  document.cookie = `${TOKEN_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

/**
 * Only allow same-origin relative paths (e.g. /dashboard/jobs/1).
 */
function safeRedirectPath(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  return raw;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    loading: true,
  });

  const setToken = useCallback((token: string | null) => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      setAuthCookie(token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      clearAuthCookie();
    }
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setState({ user: null, token: null, loading: false });
      return;
    }

    setAuthCookie(stored);
    setState((s) => ({ ...s, token: stored, loading: true }));

    api
      .me()
      .then((user) => setState({ user, token: stored, loading: false }))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        clearAuthCookie();
        setState({ user: null, token: null, loading: false });
      });
  }, []);

  const login = useCallback(
    async (email: string, password: string, redirectTo?: string | null) => {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      const user = await api.me();
      setState({ user, token: access_token, loading: false });
      const path = safeRedirectPath(redirectTo ?? null) ?? "/dashboard";
      router.push(path);
    },
    [router, setToken],
  );

  const signup = useCallback(
    async (email: string, password: string, redirectTo?: string | null) => {
      const { access_token } = await api.signup(email, password);
      setToken(access_token);
      const user = await api.me();
      setState({ user, token: access_token, loading: false });
      const path = safeRedirectPath(redirectTo ?? null) ?? "/dashboard";
      router.push(path);
    },
    [router, setToken],
  );

  const logout = useCallback(() => {
    setToken(null);
    setState({ user: null, token: null, loading: false });
    router.push("/login");
  }, [router, setToken]);

  const value = useMemo(
    () => ({ ...state, login, signup, logout }),
    [state, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { ApiError };
