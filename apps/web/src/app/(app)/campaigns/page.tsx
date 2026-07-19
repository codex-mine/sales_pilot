"use client";

import { useState } from "react";
import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Plus } from "@/icons";
import { CampaignFormDrawer } from "@/features/campaigns/components/campaign-form-drawer";
import { CampaignsTable } from "@/features/campaigns/components/campaigns-table";
import type { CampaignResponse } from "@/features/campaigns/types";

function CampaignsPageContent(): React.ReactElement {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<CampaignResponse | undefined>(undefined);

  return (
    <PageLayout>
      <PageHeader
        title="Campaigns"
        description="Multi-step outreach sequences — enroll leads, automate sends, and track replies."
        actions={
          <Button
            onClick={() => {
              setEditingCampaign(undefined);
              setDrawerOpen(true);
            }}
          >
            <Plus className="size-4" />
            Create campaign
          </Button>
        }
      />

      <PermissionGuard permission="campaigns.read">
        <CampaignsTable
          onEditCampaign={(campaign) => {
            setEditingCampaign(campaign);
            setDrawerOpen(true);
          }}
          onCreateCampaign={() => {
            setEditingCampaign(undefined);
            setDrawerOpen(true);
          }}
        />
      </PermissionGuard>

      <CampaignFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} campaign={editingCampaign} />
    </PageLayout>
  );
}

export default function CampaignsPage(): React.ReactElement {
  return <CampaignsPageContent />;
}
