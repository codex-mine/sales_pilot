"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertTriangle, CheckCircle2 } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { AcceptInvitationForm } from "@/features/organizations/components/accept-invitation-form";

export interface AcceptInvitationPageContentProps {
  token: string | null;
}

type ViewState = "form" | "success" | "invalid";

export function AcceptInvitationPageContent({ token }: AcceptInvitationPageContentProps): React.ReactElement {
  const [view, setView] = useState<ViewState>(token ? "form" : "invalid");
  const router = useRouter();

  if (view === "invalid") {
    return (
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard title="Invitation expired or invalid">
          <EmptyState
            icon={AlertTriangle}
            title="This invitation no longer works"
            description="Invitations expire after 7 days, can only be used once, and may have been revoked. Ask whoever invited you to send a new one."
            action={
              <Button asChild size="sm">
                <Link href="/login">Back to sign in</Link>
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
        <AuthCard title="Welcome aboard">
          <EmptyState
            icon={CheckCircle2}
            title="You've joined the workspace"
            description="Your account is ready to go."
            action={
              <Button size="sm" onClick={() => router.replace("/dashboard")}>
                Go to dashboard
              </Button>
            }
          />
        </AuthCard>
      </CenteredLayout>
    );
  }

  return (
    <CenteredLayout maxWidthClassName="max-w-md">
      <AuthCard title="Accept your invitation" description="Set your name and password to join the workspace.">
        <AcceptInvitationForm
          token={token as string}
          onSuccess={() => setView("success")}
          onInvalidToken={() => setView("invalid")}
        />
      </AuthCard>
    </CenteredLayout>
  );
}
