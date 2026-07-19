import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { BreadcrumbTrail } from "@/components/ui/breadcrumb";
import { CampaignDetailContent } from "@/features/campaigns/components/campaign-detail-content";

export default async function CampaignDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.ReactElement> {
  const { id } = await params;

  return (
    <PageLayout>
      <BreadcrumbTrail
        items={[{ label: "Campaigns", href: "/campaigns" }, { label: "Campaign details" }]}
        className="mb-4"
      />
      <PermissionGuard permission="campaigns.read">
        <CampaignDetailContent campaignId={id} />
      </PermissionGuard>
    </PageLayout>
  );
}
