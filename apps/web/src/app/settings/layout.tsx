import type { ReactNode } from "react";
import { AuthGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";

export default function SettingsLayout({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <PageLayout>
          <PageHeader title="Settings" description="Manage your account, security, and workspace." />
          {children}
        </PageLayout>
      </AppShell>
    </AuthGuard>
  );
}
