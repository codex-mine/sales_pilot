"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertTriangle, CheckCircle2 } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { ResetPasswordForm } from "@/features/auth/components/reset-password-form";

export interface ResetPasswordPageContentProps {
  token: string | null;
}

type ViewState = "form" | "success" | "invalid";

export function ResetPasswordPageContent({ token }: ResetPasswordPageContentProps): React.ReactElement {
  const [view, setView] = useState<ViewState>(token ? "form" : "invalid");
  const router = useRouter();

  if (view === "invalid") {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Link expired or invalid">
          <EmptyState
            icon={AlertTriangle}
            title="This reset link no longer works"
            description="Password reset links expire after 30 minutes and can only be used once. Request a new one to continue."
            action={
              <Button asChild size="sm">
                <Link href="/forgot-password">Request a new link</Link>
              </Button>
            }
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  if (view === "success") {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Password reset">
          <EmptyState
            icon={CheckCircle2}
            title="Your password has been reset"
            description="All existing sessions have been signed out for your security. Sign in with your new password."
            action={
              <Button size="sm" onClick={() => router.push("/login")}>
                Continue to sign in
              </Button>
            }
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  return (
    <CenteredLayout maxWidthClassName="max-w-sm">
      <AuthCard title="Set a new password" description="Choose a strong password you haven't used before.">
        <ResetPasswordForm
          token={token as string}
          onSuccess={() => setView("success")}
          onInvalidToken={() => setView("invalid")}
        />
      </AuthCard>
    </CenteredLayout>
  );
}
