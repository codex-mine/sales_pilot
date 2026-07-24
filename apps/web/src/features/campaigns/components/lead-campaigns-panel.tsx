"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, Rocket, UserMinus } from "@/icons";
import { useUnenrollCampaignLead } from "../hooks/use-campaign-enrollment";
import { useLeadCampaigns } from "../hooks/use-lead-campaigns";
import type { CampaignLeadResponse } from "../types";
import { CampaignLeadStatusBadge } from "./campaign-lead-status-badge";

export interface LeadCampaignsPanelProps {
  leadId: string;
}

export function LeadCampaignsPanel({ leadId }: LeadCampaignsPanelProps): React.ReactElement {
  const { campaignLeads, isLoading, isError, errorMessage } = useLeadCampaigns(leadId);
  const { unenroll, isUnenrolling } = useUnenrollCampaignLead();
  const [pendingUnenroll, setPendingUnenroll] = useState<CampaignLeadResponse | null>(null);
  const unenrollConfirm = useConfirmDialog();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Couldn't load campaigns"
        description={errorMessage ?? "Something went wrong while loading this lead's campaign enrollments."}
      />
    );
  }

  async function handleConfirmUnenroll(): Promise<void> {
    if (!pendingUnenroll) return;
    await unenroll({ campaignId: pendingUnenroll.campaign_id, campaignLeadId: pendingUnenroll.id });
    unenrollConfirm.close();
    setPendingUnenroll(null);
  }

  if (campaignLeads.length === 0) {
    return (
      <EmptyState
        icon={Rocket}
        title="Not enrolled in any campaign"
        description="Add this lead to a campaign from the Leads table to start an automated sequence."
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {campaignLeads.map((campaignLead) => (
        <Card key={campaignLead.id}>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <Link href={`/campaigns/${campaignLead.campaign_id}`} className="text-body-md font-medium text-foreground hover:underline">
                  {campaignLead.campaign_name ?? "Campaign"}
                </Link>
                <CampaignLeadStatusBadge status={campaignLead.status} />
              </div>
              <p className="text-body-sm text-muted-foreground">
                Step {campaignLead.current_step_order}
                {campaignLead.next_step_type && ` -> ${campaignLead.next_step_type}`}
                {campaignLead.next_action_at &&
                  ` · next action ${formatDistanceToNow(new Date(campaignLead.next_action_at), { addSuffix: true })}`}
              </p>
            </div>
            {!campaignLead.opted_out_at && campaignLead.status !== "completed" && (
              <Button
                variant="ghost"
                size="sm"
                className="text-danger"
                onClick={() => {
                  setPendingUnenroll(campaignLead);
                  unenrollConfirm.open();
                }}
              >
                <UserMinus className="size-4" />
                Unenroll
              </Button>
            )}
          </CardContent>
        </Card>
      ))}

      <ConfirmDialog
        open={unenrollConfirm.isOpen}
        onOpenChange={unenrollConfirm.onOpenChange}
        title="Unenroll from this campaign?"
        description="This lead will stop receiving further steps in this campaign."
        confirmLabel="Unenroll"
        isConfirming={isUnenrolling}
        onConfirm={handleConfirmUnenroll}
      />
    </div>
  );
}
