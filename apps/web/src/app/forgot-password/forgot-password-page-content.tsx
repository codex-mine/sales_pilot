"use client";

import Link from "next/link";
import { useState } from "react";
import { MailCheck } from "@/icons";
import { EmptyState } from "@/components/ui/empty-state";
import { GuestGuard } from "@/components/guards";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form";

export function ForgotPasswordPageContent(): React.ReactElement {
  const [sentTo, setSentTo] = useState<string | null>(null);

  return (
    <GuestGuard>
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard
          title={sentTo ? "Check your email" : "Forgot your password?"}
          description={sentTo ? undefined : "Enter your email and we'll send you a reset link."}
          footer={
            <Link href="/login" className="font-medium text-primary hover:underline">
              Back to sign in
            </Link>
          }
        >
          {sentTo ? (
            <EmptyState
              icon={MailCheck}
              title="Reset link sent"
              description={`If an account exists for ${sentTo}, you'll receive an email with a link to reset your password shortly.`}
            />
          ) : (
            <ForgotPasswordForm onSuccess={setSentTo} />
          )}
        </AuthCard>
      </CenteredLayout>
    </GuestGuard>
  );
}
