"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { AccessDenied } from "./access-denied";

export interface PermissionGuardProps {
  children: ReactNode;
  /** A single permission, or a list combined per `match`. */
  permission: string | string[];
  /** "any" (default) requires at least one; "all" requires every listed permission. */
  match?: "any" | "all";
  redirectTo?: string;
  fallback?: ReactNode;
}

/** Gates `children` on an RBAC permission check (`resource.action`). Assumes it's rendered inside an `AuthGuard`. */
export function PermissionGuard({
  children,
  permission,
  match = "any",
  redirectTo,
  fallback,
}: PermissionGuardProps): React.ReactElement {
  const { hasAnyPermission, hasAllPermissions } = usePermissions();
  const router = useRouter();
  const required = Array.isArray(permission) ? permission : [permission];
  const allowed = match === "all" ? hasAllPermissions(required) : hasAnyPermission(required);

  useEffect(() => {
    if (!allowed && redirectTo) router.replace(redirectTo);
  }, [allowed, redirectTo, router]);

  if (!allowed) {
    if (redirectTo) return <></>;
    return <>{fallback ?? <AccessDenied />}</>;
  }

  return <>{children}</>;
}
