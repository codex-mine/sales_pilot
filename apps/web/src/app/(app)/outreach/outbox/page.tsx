"use client";

import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";
import { OutboxTable } from "@/features/leads/components/outbox-table";

function OutboxPageContent(): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader
        title="Outbox"
        description="Every email across your leads — draft, scheduled, sending, sent, and failed — in one place."
      />
      <PermissionGuard permission="leads.read">
        <OutboxTable />
      </PermissionGuard>
    </PageLayout>
  );
}

export default function OutboxPage(): React.ReactElement {
  return <OutboxPageContent />;
}
