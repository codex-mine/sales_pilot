"use client";

import { useAuthStore } from "@/store/auth-store";

/**
 * The primary auth hook: current user/org/workspace, auth status, and the
 * core actions (login/logout/logoutAll/refresh). Most components want this;
 * reach for `useCurrentUser`/`usePermissions`/`useRole` instead only when a
 * narrower selector avoids an unnecessary re-render.
 */
export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const organization = useAuthStore((state) => state.organization);
  const workspace = useAuthStore((state) => state.workspace);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitialized = useAuthStore((state) => state.isInitialized);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const logoutAll = useAuthStore((state) => state.logoutAll);
  const refresh = useAuthStore((state) => state.refresh);
  const initialize = useAuthStore((state) => state.initialize);

  return {
    user,
    organization,
    workspace,
    isAuthenticated,
    isInitialized,
    isLoading,
    error,
    login,
    logout,
    logoutAll,
    refresh,
    initialize,
  };
}
