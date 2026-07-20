"use client";

import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { PageHeader } from "@/components/ui/page-header";
import { EmailTemplatesTable } from "@/features/email-templates/components/email-templates-table";

function EmailTemplatesPageContent(): React.ReactElement {
  return (
    <PageLayout>
      <PageHeader
        title="Email Templates"
        description="Reusable email content — both AI-generated and hand-written. Approve a generated email as a template to see it here."
      />
      <PermissionGuard permission="campaigns.read">
        <EmailTemplatesTable />
      </PermissionGuard>
    </PageLayout>
  );
}

export default function EmailTemplatesPage(): React.ReactElement {
  return <EmailTemplatesPageContent />;
}
