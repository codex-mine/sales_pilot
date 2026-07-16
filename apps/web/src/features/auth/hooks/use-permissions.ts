"use client";

import { useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";

export interface UsePermissionsReturn {
  permissions: string[];
  /** Exact match, or `<resource>.manage` (which implies every action on that resource — same rule the backend's RBACService applies). */
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

/** RBAC permission checks against the flattened `resource.action` list from `/auth/me`. */
export function usePermissions(): UsePermissionsReturn {
  const permissions = useAuthStore((state) => state.permissions);

  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (permissions.includes(permission)) return true;
      const [resource] = permission.split(".");
      return permissions.includes(`${resource}.manage`);
    },
    [permissions],
  );

  const hasAnyPermission = useCallback(
    (required: string[]): boolean => required.some(hasPermission),
    [hasPermission],
  );

  const hasAllPermissions = useCallback(
    (required: string[]): boolean => required.every(hasPermission),
    [hasPermission],
  );

  return { permissions, hasPermission, hasAnyPermission, hasAllPermissions };
}
