"use client";

import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";
import { MeetingsTable } from "@/features/meetings/components/meetings-table";

export default function MeetingsPage(): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader title="Meetings" description="Every meeting across your leads — proposed, confirmed, and completed." />
      <PermissionGuard permission="leads.read">
        <MeetingsTable />
      </PermissionGuard>
    </PageLayout>
  );
}
