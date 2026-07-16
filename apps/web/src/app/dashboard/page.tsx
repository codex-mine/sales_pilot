"use client";

import { LayoutDashboard, MailWarning } from "@/icons";
import { AuthGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { authService } from "@/features/auth/services/auth.service";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

function DashboardContent(): React.ReactElement {
  const user = useCurrentUser();

  const resendMutation = useMutation({
    mutationFn: () => authService.resendVerification(),
    onSuccess: () => toast.success("Verification email sent."),
  });

  return (
    <PageLayout>
      <PageHeader
        title={user ? `Welcome back, ${user.first_name}` : "Dashboard"}
        description="Here's what's happening in your workspace."
      />

      {user && !user.email_verified && (
        <Alert variant="warning" icon={MailWarning} className="mb-6">
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>Verify your email address to unlock all features.</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => resendMutation.mutate()}
              isLoading={resendMutation.isPending}
            >
              Resend email
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <EmptyState
        icon={LayoutDashboard}
        title="Your dashboard is ready"
        description="Campaigns, leads, and AI insights will appear here as those features come online."
      />
    </PageLayout>
  );
}

export default function DashboardPage(): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <DashboardContent />
      </AppShell>
    </AuthGuard>
  );
}
