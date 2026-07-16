"use client";

import { useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";

// Mirrors the backend's ROLE_PRIORITY table (app/security/permissions.py) —
// lower index = higher privilege. Kept in sync manually since roles are a
// small, stable set; if the backend's system roles ever change, update here too.
const ROLE_PRIORITY = ["owner", "admin", "manager", "sales", "member", "viewer"];

export interface UseRoleReturn {
  /** The user's highest-privilege role name, or null if they hold no role in this org. */
  primaryRole: string | null;
  roles: string[];
  hasRole: (role: string) => boolean;
  /** True if the user holds `role` or anything higher-privileged (e.g. `atLeast("admin")` is also true for an owner). */
  atLeast: (role: string) => boolean;
}

export function useRole(): UseRoleReturn {
  const roles = useAuthStore((state) => state.roles);
  const primaryRole = useAuthStore((state) => state.user?.role ?? null);

  const hasRole = useCallback((role: string): boolean => roles.includes(role), [roles]);

  const atLeast = useCallback(
    (role: string): boolean => {
      const requiredPriority = ROLE_PRIORITY.indexOf(role);
      if (requiredPriority === -1) return hasRole(role);
      const bestPriority = Math.min(
        ...roles.map((r) => {
          const priority = ROLE_PRIORITY.indexOf(r);
          return priority === -1 ? ROLE_PRIORITY.length : priority;
        }),
      );
      return bestPriority <= requiredPriority;
    },
    [roles, hasRole],
  );

  return { primaryRole, roles, hasRole, atLeast };
}
