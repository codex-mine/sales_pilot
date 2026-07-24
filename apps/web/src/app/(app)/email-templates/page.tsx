"use client";

import { useState } from "react";
import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Plus } from "@/icons";
import { EmailTemplateFormDrawer } from "@/features/email-templates/components/email-template-form-drawer";
import { EmailTemplatesTable } from "@/features/email-templates/components/email-templates-table";

function EmailTemplatesPageContent(): React.ReactElement {
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <PageLayout>
      <PageHeader
        title="Email Templates"
        description="Reusable email content — both AI-generated and hand-written."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            Create template
          </Button>
        }
      />
      <PermissionGuard permission="campaigns.read">
        <EmailTemplatesTable />
      </PermissionGuard>
      <EmailTemplateFormDrawer open={createOpen} onOpenChange={setCreateOpen} />
    </PageLayout>
  );
}

export default function EmailTemplatesPage(): React.ReactElement {
  return <EmailTemplatesPageContent />;
}
