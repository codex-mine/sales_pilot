import type { ReactNode } from "react";
import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";

export default function AILayout({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <PageLayout>
          <PageHeader
            title="AI"
            description="Every AI call the system makes — providers, agents, prompts, jobs, and spend — in one place."
          />
          <PermissionGuard permission="ai.read" redirectTo="/dashboard">
            {children}
          </PermissionGuard>
        </PageLayout>
      </AppShell>
    </AuthGuard>
  );
}
