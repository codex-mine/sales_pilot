"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { AuthLoadingScreen } from "./auth-loading-screen";

export interface AuthGuardProps {
  children: ReactNode;
}

/**
 * Protects a route: renders nothing (a loading screen) until auth
 * initialization has settled, then redirects to `/login` (preserving the
 * attempted path as `?redirect=`) if the visitor isn't authenticated.
 * Never renders `children` before both conditions are confirmed.
 */
export function AuthGuard({ children }: AuthGuardProps): React.ReactElement {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      const redirect = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?redirect=${redirect}`);
    }
  }, [isInitialized, isAuthenticated, pathname, router]);

  if (!isInitialized || !isAuthenticated) {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}
