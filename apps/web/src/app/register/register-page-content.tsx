"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { MailCheck } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { GuestGuard } from "@/components/guards";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { RegisterForm } from "@/features/auth/components/register-form";
import { authService } from "@/features/auth/services/auth.service";

/**
 * Registration auto-logs the new owner in (the backend sets session cookies
 * in the same response), so once `registeredEmail` is set the visitor is
 * genuinely authenticated — this success screen must render *outside*
 * `<GuestGuard>`, which would otherwise immediately redirect an authenticated
 * visitor to `/dashboard` before they ever see it.
 */
export function RegisterPageContent(): React.ReactElement {
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const resendMutation = useMutation({
    mutationFn: () => authService.resendVerification(),
  });

  if (registeredEmail) {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Check your email">
          <EmptyState
            icon={MailCheck}
            title="Verify your email address"
            description={`We sent a verification link to ${registeredEmail}. Follow it to activate your account, or continue to your dashboard now — some actions will be limited until you verify.`}
            action={
              <div className="flex flex-col gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => resendMutation.mutate()}
                  isLoading={resendMutation.isPending}
                >
                  Resend email
                </Button>
                <Button asChild size="sm">
                  <Link href="/dashboard">Continue to dashboard</Link>
                </Button>
              </div>
            }
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  return (
    <GuestGuard>
      <CenteredLayout maxWidthClassName="max-w-md">
        <AuthCard
          title="Create your workspace"
          description="Start your 14-day trial. No credit card required."
          footer={
            <>
              Already have an account?{" "}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </>
          }
        >
          <RegisterForm onSuccess={setRegisteredEmail} />
        </AuthCard>
      </CenteredLayout>
    </GuestGuard>
  );
}
