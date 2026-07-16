"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useRole } from "@/features/auth/hooks/use-role";
import { AccessDenied } from "./access-denied";

export interface RoleGuardProps {
  children: ReactNode;
  /** Required role. Combine with `atLeast` to allow that role or anything higher-privileged. */
  role: string;
  atLeast?: boolean;
  /** If set, redirects here instead of rendering the inline "Access denied" state. */
  redirectTo?: string;
  fallback?: ReactNode;
}

/** Gates `children` on the current user holding (or outranking) `role`. Assumes it's rendered inside an `AuthGuard`. */
export function RoleGuard({
  children,
  role,
  atLeast = false,
  redirectTo,
  fallback,
}: RoleGuardProps): React.ReactElement {
  const { hasRole, atLeast: meetsMinimumRole } = useRole();
  const router = useRouter();
  const allowed = atLeast ? meetsMinimumRole(role) : hasRole(role);

  useEffect(() => {
    if (!allowed && redirectTo) router.replace(redirectTo);
  }, [allowed, redirectTo, router]);

  if (!allowed) {
    if (redirectTo) return <></>;
    return <>{fallback ?? <AccessDenied />}</>;
  }

  return <>{children}</>;
}
