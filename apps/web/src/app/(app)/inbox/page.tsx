"use client";

import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";
import { InboxPageContent } from "@/features/inbox/components/inbox-page-content";

export default function Page(): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader title="Inbox" description="Replies from your leads, AI-classified and ready to action." />
      <PermissionGuard permission="leads.read">
        <InboxPageContent />
      </PermissionGuard>
    </PageLayout>
  );
}
