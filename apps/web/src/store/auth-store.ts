import { create } from "zustand";
import type { AuthUser } from "@/types/api";

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  setAuth: (payload: { accessToken: string; user: AuthUser }) => void;
  clearAuth: () => void;
  hydrateFromStorage: () => void;
}

const storageKey = "salespilot-auth";

function readStoredAuth() {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.sessionStorage.getItem(storageKey);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isHydrated: false,
  setAuth: ({ accessToken, user }) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({ accessToken, user }),
      );
      document.cookie = "auth_session=1; path=/; max-age=86400; samesite=lax";
    }

    set({ accessToken, user, isAuthenticated: true, isHydrated: true });
  },
  clearAuth: () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(storageKey);
      document.cookie = "auth_session=; path=/; max-age=0";
    }

    set({ accessToken: null, user: null, isAuthenticated: false, isHydrated: true });
  },
  hydrateFromStorage: () => {
    const stored = readStoredAuth();

    if (stored?.accessToken && stored?.user) {
      set({
        accessToken: stored.accessToken,
        user: stored.user,
        isAuthenticated: true,
        isHydrated: true,
      });
      return;
    }

    set({ isHydrated: true });
  },
}));
