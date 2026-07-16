"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, MailWarning } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { authService } from "@/features/auth/services/auth.service";

export interface VerifyEmailPageContentProps {
  token: string | null;
}

const REDIRECT_COUNTDOWN_SECONDS = 5;

export function VerifyEmailPageContent({ token }: VerifyEmailPageContentProps): React.ReactElement {
  const router = useRouter();
  const { isAuthenticated, isInitialized } = useAuth();
  const [countdown, setCountdown] = useState(REDIRECT_COUNTDOWN_SECONDS);
  const hasRun = useRef(false);

  const verifyMutation = useMutation({
    mutationFn: (verifyToken: string) => authService.verifyEmail({ token: verifyToken }),
  });

  const resendMutation = useMutation({
    mutationFn: () => authService.resendVerification(),
  });

  useEffect(() => {
    if (!token || hasRun.current) return;
    hasRun.current = true;
    verifyMutation.mutate(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!verifyMutation.isSuccess) return;
    if (countdown <= 0) {
      router.replace(isAuthenticated ? "/dashboard" : "/login");
      return;
    }
    const timer = setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [verifyMutation.isSuccess, countdown, isAuthenticated, router]);

  if (!token) {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Invalid link">
          <EmptyState
            icon={AlertTriangle}
            title="Missing verification token"
            description="This link is missing its verification token. Please use the exact link from your email."
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  if (verifyMutation.isPending || !isInitialized) {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Verifying your email">
          <div className="flex flex-col items-center gap-3 py-6">
            <Loader2 className="size-6 animate-spin text-primary" />
            <p className="text-body-sm text-muted-foreground">Please wait a moment...</p>
          </div>
        </AuthCard>
      </CenteredLayout>
    );
  }

  if (verifyMutation.isSuccess) {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Email verified">
          <EmptyState
            icon={CheckCircle2}
            title="Your email has been verified"
            description={`Redirecting you in ${countdown}s...`}
            action={
              <Button size="sm" onClick={() => router.replace(isAuthenticated ? "/dashboard" : "/login")}>
                {isAuthenticated ? "Go to dashboard now" : "Go to sign in now"}
              </Button>
            }
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  // Verification failed — the backend deliberately doesn't distinguish
  // "invalid" from "expired" (same generic message either way), so this one
  // screen covers both cases from Step 8.
  return (
    <CenteredLayout maxWidthClassName="max-w-sm">
      <AuthCard title="Verification link expired">
        <EmptyState
          icon={MailWarning}
          title="This link is invalid or has expired"
          description={
            isAuthenticated
              ? "Verification links expire after 24 hours. Request a new one below."
              : "Verification links expire after 24 hours. Sign in, then request a new one from your account."
          }
          action={
            isAuthenticated ? (
              <Button
                size="sm"
                onClick={() => resendMutation.mutate()}
                isLoading={resendMutation.isPending}
                disabled={resendMutation.isSuccess}
              >
                {resendMutation.isSuccess ? "New link sent" : "Resend verification email"}
              </Button>
            ) : (
              <Button asChild size="sm">
                <Link href="/login">Sign in</Link>
              </Button>
            )
          }
        />
      </AuthCard>
    </CenteredLayout>
  );
}
