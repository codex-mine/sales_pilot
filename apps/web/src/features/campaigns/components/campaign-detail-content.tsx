"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Archive, Clock3, Pause, Pencil, Play, Rocket, Users } from "@/icons";
import { getInitials } from "@/lib/utils";
import { Avatar } from "@/components/ui/avatar";
import { useCampaign } from "../hooks/use-campaign";
import { useCampaignStatusControl, useDeleteCampaign } from "../hooks/use-campaign-mutations";
import { CampaignDashboardPanel } from "./campaign-dashboard-panel";
import { CampaignFormDrawer } from "./campaign-form-drawer";
import { CampaignLeadsTable } from "./campaign-leads-table";
import { CampaignStatusBadge } from "./campaign-status-badge";
import { SequenceBuilder } from "./sequence-builder";

export interface CampaignDetailContentProps {
  campaignId: string;
}

export function CampaignDetailContent({ campaignId }: CampaignDetailContentProps): React.ReactElement {
  const router = useRouter();
  const { campaign, isLoading, isError, errorMessage, refetch } = useCampaign(campaignId);
  const { activateCampaign, pauseCampaign, archiveCampaign, isActivating, isPausing, isArchiving } =
    useCampaignStatusControl();
  const { deleteCampaign, isDeleting } = useDeleteCampaign();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const deleteConfirm = useConfirmDialog();
  const archiveConfirm = useConfirmDialog();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (isError || !campaign) {
    return <ErrorState title="Couldn't load campaign" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  async function handleDelete(): Promise<void> {
    await deleteCampaign(campaignId);
    router.push("/campaigns");
  }

  async function handleArchive(): Promise<void> {
    await archiveCampaign(campaignId);
    archiveConfirm.close();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4 pt-6">
          <div className="flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-muted">
              <Rocket className="size-6 text-muted-foreground" />
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <h1 className="text-heading-4 font-semibold text-foreground">{campaign.name}</h1>
                <CampaignStatusBadge status={campaign.status} />
              </div>
              {campaign.goal && <p className="text-body-sm text-muted-foreground">{campaign.goal}</p>}
              <div className="flex flex-wrap items-center gap-3 pt-1 text-caption text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Users className="size-3.5" />
                  {campaign.enrolled_count} enrolled
                </span>
                <span className="flex items-center gap-1">
                  <Clock3 className="size-3.5" />
                  {campaign.requires_approval ? "Approval required" : "Full automation"}
                </span>
                {campaign.owner && (
                  <span className="flex items-center gap-1.5">
                    <Avatar size="xs" fallback={getInitials(campaign.owner.full_name)} />
                    {campaign.owner.full_name}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {(campaign.status === "draft" || campaign.status === "paused") && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void activateCampaign(campaignId)}
                isLoading={isActivating}
              >
                <Play className="size-4" />
                Activate
              </Button>
            )}
            {campaign.status === "active" && (
              <Button variant="outline" size="sm" onClick={() => void pauseCampaign(campaignId)} isLoading={isPausing}>
                <Pause className="size-4" />
                Pause
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)}>
              <Pencil className="size-4" />
              Edit
            </Button>
            {campaign.status !== "archived" && (
              <Button variant="outline" size="sm" onClick={archiveConfirm.open} isLoading={isArchiving}>
                <Archive className="size-4" />
                Archive
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sequence">Sequence Builder</TabsTrigger>
          <TabsTrigger value="leads">Leads ({campaign.enrolled_count})</TabsTrigger>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Targeting</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-body-sm">
                <div>
                  <dt className="text-caption text-muted-foreground">Industry</dt>
                  <dd className="text-foreground">{campaign.target_industry || "—"}</dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Company size</dt>
                  <dd className="text-foreground">{campaign.target_company_size || "—"}</dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Job titles</dt>
                  <dd className="flex flex-wrap gap-1 pt-1">
                    {campaign.target_job_titles && campaign.target_job_titles.length > 0
                      ? campaign.target_job_titles.map((title) => (
                          <Badge key={title} variant="soft">
                            {title}
                          </Badge>
                        ))
                      : "—"}
                  </dd>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Send window</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-body-sm">
                <div>
                  <dt className="text-caption text-muted-foreground">Days</dt>
                  <dd className="flex flex-wrap gap-1 pt-1">
                    {campaign.send_days.map((day) => (
                      <Badge key={day} variant="outline">
                        {day.charAt(0).toUpperCase() + day.slice(1, 3)}
                      </Badge>
                    ))}
                  </dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Hours</dt>
                  <dd className="text-foreground">
                    {String(campaign.send_start_hour).padStart(2, "0")}:00 – {String(campaign.send_end_hour).padStart(2, "0")}:00 ({campaign.timezone})
                  </dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Daily send limit</dt>
                  <dd className="text-foreground">{campaign.daily_send_limit}</dd>
                </div>
              </CardContent>
            </Card>

            {campaign.value_proposition && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Value proposition</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body-sm text-foreground">{campaign.value_proposition}</p>
                </CardContent>
              </Card>
            )}

            {campaign.description && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body-sm text-foreground">{campaign.description}</p>
                </CardContent>
              </Card>
            )}

            <Card className="border-danger/40 lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-danger">Danger zone</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-body-sm font-medium text-foreground">Delete this campaign</p>
                  <p className="text-body-sm text-muted-foreground">
                    {campaign.status === "active"
                      ? "Pause or archive an active campaign before deleting it."
                      : "This permanently deletes the campaign. This cannot be undone."}
                  </p>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={deleteConfirm.open}
                  disabled={campaign.status === "active"}
                >
                  Delete
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sequence">
          <SequenceBuilder campaignId={campaignId} />
        </TabsContent>

        <TabsContent value="leads">
          <CampaignLeadsTable campaignId={campaignId} />
        </TabsContent>

        <TabsContent value="dashboard">
          <CampaignDashboardPanel campaignId={campaignId} />
        </TabsContent>
      </Tabs>

      <CampaignFormDrawer open={isEditOpen} onOpenChange={setIsEditOpen} campaign={campaign} />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this campaign?"
        description={`This permanently deletes "${campaign.name}". This cannot be undone.`}
        confirmLabel="Delete campaign"
        isConfirming={isDeleting}
        onConfirm={handleDelete}
      />
      <ConfirmDialog
        open={archiveConfirm.isOpen}
        onOpenChange={archiveConfirm.onOpenChange}
        title="Archive this campaign?"
        description="Archived campaigns stop processing enrolled leads permanently — this cannot be undone."
        confirmLabel="Archive campaign"
        isConfirming={isArchiving}
        onConfirm={handleArchive}
      />
    </div>
  );
}
