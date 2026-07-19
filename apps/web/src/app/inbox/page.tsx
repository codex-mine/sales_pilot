"use client";

import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";
import { InboxPageContent } from "@/features/inbox/components/inbox-page-content";

function InboxPage(): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader title="Inbox" description="Replies from your leads, AI-classified and ready to action." />
      <PermissionGuard permission="leads.read">
        <InboxPageContent />
      </PermissionGuard>
    </PageLayout>
  );
}

export default function Page(): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <InboxPage />
      </AppShell>
    </AuthGuard>
  );
}
