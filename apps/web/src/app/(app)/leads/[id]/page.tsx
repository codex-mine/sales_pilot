import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { BreadcrumbTrail } from "@/components/ui/breadcrumb";
import { LeadDetailContent } from "@/features/leads/components/lead-detail-content";

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.ReactElement> {
  const { id } = await params;

  return (
    <PageLayout>
      <BreadcrumbTrail
        items={[{ label: "Leads", href: "/leads" }, { label: "Lead details" }]}
        className="mb-4"
      />
      <PermissionGuard permission="leads.read">
        <LeadDetailContent leadId={id} />
      </PermissionGuard>
    </PageLayout>
  );
}
