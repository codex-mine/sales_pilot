"use client";

import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { BreadcrumbTrail } from "@/components/ui/breadcrumb";
import { PageHeader } from "@/components/ui/page-header";
import { LeadImportWizard } from "@/features/leads/components/lead-import-wizard";

function LeadImportPageContent(): React.ReactElement {
  return (
    <PageLayout>
      <BreadcrumbTrail items={[{ label: "Leads", href: "/leads" }, { label: "Import" }]} className="mb-4" />
      <PageHeader title="Import leads" description="Upload a CSV file to bulk-add leads to your pipeline." />
      <PermissionGuard permission="leads.import">
        <LeadImportWizard />
      </PermissionGuard>
    </PageLayout>
  );
}

export default function LeadImportPage(): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <LeadImportPageContent />
      </AppShell>
    </AuthGuard>
  );
}
