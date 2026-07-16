"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { AuthLoadingScreen } from "./auth-loading-screen";

export interface GuestGuardProps {
  children: ReactNode;
}

/**
 * Protects a guest-only route (login, register, forgot-password): once
 * initialization confirms the visitor is already authenticated, redirects
 * them straight to `/dashboard` (or `?redirect=` if one was set) instead of
 * showing the login form again.
 */
export function GuestGuard({ children }: GuestGuardProps): React.ReactElement {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (isInitialized && isAuthenticated) {
      const redirect = searchParams.get("redirect");
      router.replace(redirect ? decodeURIComponent(redirect) : "/dashboard");
    }
  }, [isInitialized, isAuthenticated, router, searchParams]);

  if (!isInitialized || isAuthenticated) {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}
