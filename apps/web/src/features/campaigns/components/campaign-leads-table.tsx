"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { UserMinus, UserPlus, Users } from "@/icons";
import { useUnenrollCampaignLead } from "../hooks/use-campaign-enrollment";
import { useCampaignLeads } from "../hooks/use-campaign-leads";
import { CAMPAIGN_LEAD_STATUS_CHOICES, CAMPAIGN_LEAD_STATUS_LABELS, type CampaignLeadResponse } from "../types";
import { CampaignLeadStatusBadge } from "./campaign-lead-status-badge";
import { EnrollLeadsDialog } from "./enroll-leads-dialog";

const STATUS_OPTIONS: MultiSelectOption[] = CAMPAIGN_LEAD_STATUS_CHOICES.map((status) => ({
  value: status,
  label: CAMPAIGN_LEAD_STATUS_LABELS[status],
}));

export interface CampaignLeadsTableProps {
  campaignId: string;
}

export function CampaignLeadsTable({ campaignId }: CampaignLeadsTableProps): React.ReactElement {
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [pendingUnenroll, setPendingUnenroll] = useState<CampaignLeadResponse | null>(null);
  const unenrollConfirm = useConfirmDialog();

  const { campaignLeads, isLoading } = useCampaignLeads(campaignId, {
    status: statusFilter.length ? statusFilter : undefined,
    page_size: 100,
  });
  const { unenroll, isUnenrolling } = useUnenrollCampaignLead();

  async function handleConfirmUnenroll(): Promise<void> {
    if (!pendingUnenroll) return;
    await unenroll({ campaignId, campaignLeadId: pendingUnenroll.id });
    unenrollConfirm.close();
    setPendingUnenroll(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <MultiSelect
          options={STATUS_OPTIONS}
          values={statusFilter}
          onValuesChange={setStatusFilter}
          placeholder="Status"
          className="w-48"
        />
        <Button size="sm" onClick={() => setEnrollOpen(true)}>
          <UserPlus className="size-4" />
          Enroll leads
        </Button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : campaignLeads.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No leads enrolled"
          description="Enroll leads to start moving them through this campaign's sequence."
          action={
            <Button size="sm" onClick={() => setEnrollOpen(true)}>
              Enroll leads
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Lead</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Current step</TableHead>
                <TableHead>Next action</TableHead>
                <TableHead>Enrolled</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaignLeads.map((campaignLead) => (
                <TableRow key={campaignLead.id}>
                  <TableCell>
                    {campaignLead.lead ? (
                      <Link href={`/leads/${campaignLead.lead.id}`} className="hover:underline">
                        <div className="flex flex-col">
                          <span className="text-body-sm font-medium text-foreground">{campaignLead.lead.full_name}</span>
                          {campaignLead.lead.company_name && (
                            <span className="text-caption text-muted-foreground">{campaignLead.lead.company_name}</span>
                          )}
                        </div>
                      </Link>
                    ) : (
                      <span className="text-body-sm text-muted-foreground">Lead removed</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <CampaignLeadStatusBadge status={campaignLead.status} />
                  </TableCell>
                  <TableCell>
                    <span className="text-body-sm text-foreground">
                      Step {campaignLead.current_step_order}
                      {campaignLead.next_step_type && ` -> ${campaignLead.next_step_type}`}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-body-sm text-muted-foreground">
                      {campaignLead.next_action_at
                        ? formatDistanceToNow(new Date(campaignLead.next_action_at), { addSuffix: true })
                        : "—"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-body-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(campaignLead.enrolled_at), { addSuffix: true })}
                    </span>
                  </TableCell>
                  <TableCell>
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
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <EnrollLeadsDialog open={enrollOpen} onOpenChange={setEnrollOpen} campaignId={campaignId} />
      <ConfirmDialog
        open={unenrollConfirm.isOpen}
        onOpenChange={unenrollConfirm.onOpenChange}
        title="Unenroll this lead?"
        description={`${pendingUnenroll?.lead?.full_name ?? "This lead"} will stop receiving further steps in this campaign.`}
        confirmLabel="Unenroll"
        isConfirming={isUnenrolling}
        onConfirm={handleConfirmUnenroll}
      />
    </div>
  );
}
