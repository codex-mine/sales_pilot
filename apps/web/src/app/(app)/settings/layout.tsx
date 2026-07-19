import type { ReactNode } from "react";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";

export default function SettingsLayout({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader title="Settings" description="Manage your account, security, and workspace." />
      {children}
    </PageLayout>
  );
}
