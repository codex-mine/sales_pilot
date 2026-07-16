"use client";

import { useMutation } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { MailWarning } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { authService } from "@/features/auth/services/auth.service";
import { normalizeApiError } from "@/lib/api/errors";

export interface VerifiedEmailGuardProps {
  children: ReactNode;
}

/** Gates `children` on `user.email_verified`, offering an inline resend action instead of a dead end. Assumes it's rendered inside an `AuthGuard`. */
export function VerifiedEmailGuard({ children }: VerifiedEmailGuardProps): React.ReactElement {
  const user = useCurrentUser();
  const [sentTo, setSentTo] = useState<string | null>(null);

  const resendMutation = useMutation({
    mutationFn: () => authService.resendVerification(),
    onSuccess: () => setSentTo(user?.email ?? null),
  });

  if (user?.email_verified) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <EmptyState
        icon={MailWarning}
        title="Verify your email to continue"
        description={
          sentTo
            ? `We sent a new verification link to ${sentTo}. Follow it to unlock this page.`
            : "Please verify your email address to access this page."
        }
        action={
          !sentTo && (
            <Button
              size="sm"
              onClick={() => resendMutation.mutate()}
              isLoading={resendMutation.isPending}
            >
              Resend verification email
            </Button>
          )
        }
      />
      {resendMutation.isError && (
        <p className="mt-2 text-body-sm text-danger">
          {normalizeApiError(resendMutation.error).message}
        </p>
      )}
    </div>
  );
}
