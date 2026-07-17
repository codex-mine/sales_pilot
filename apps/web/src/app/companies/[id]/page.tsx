import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { BreadcrumbTrail } from "@/components/ui/breadcrumb";
import { CompanyDetailContent } from "@/features/companies/components/company-detail-content";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.ReactElement> {
  const { id } = await params;

  return (
    <AuthGuard>
      <AppShell>
        <PageLayout>
          <BreadcrumbTrail
            items={[{ label: "Companies", href: "/companies" }, { label: "Company details" }]}
            className="mb-4"
          />
          <PermissionGuard permission="companies.read">
            <CompanyDetailContent companyId={id} />
          </PermissionGuard>
        </PageLayout>
      </AppShell>
    </AuthGuard>
  );
}
