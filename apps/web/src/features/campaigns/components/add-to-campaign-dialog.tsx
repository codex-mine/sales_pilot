"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCampaigns } from "../hooks/use-campaigns";
import { useBulkEnrollLeads } from "../hooks/use-campaign-enrollment";

export interface AddToCampaignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadIds: string[];
  onEnrolled?: () => void;
}

/** Bulk-enroll leads already selected elsewhere (e.g. the Leads table's row
 * selection) into a chosen campaign — just a campaign picker, since the lead
 * set is already decided by the caller. */
export function AddToCampaignDialog({ open, onOpenChange, leadIds, onEnrolled }: AddToCampaignDialogProps): React.ReactElement {
  const [campaignId, setCampaignId] = useState<string>("");
  const { campaigns, isLoading } = useCampaigns({ status: ["draft", "active"], page_size: 100 });
  const { bulkEnroll, isEnrolling } = useBulkEnrollLeads();

  async function handleEnroll(): Promise<void> {
    if (!campaignId) return;
    await bulkEnroll({ campaignId, payload: { lead_ids: leadIds } });
    setCampaignId("");
    onOpenChange(false);
    onEnrolled?.();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Add to campaign</DialogTitle>
          <DialogDescription>
            Enroll {leadIds.length} lead{leadIds.length === 1 ? "" : "s"} into a campaign&apos;s active sequence.
          </DialogDescription>
        </DialogHeader>
        <Select value={campaignId} onValueChange={setCampaignId} disabled={isLoading}>
          <SelectTrigger>
            <SelectValue placeholder="Select a campaign" />
          </SelectTrigger>
          <SelectContent>
            {campaigns.map((campaign) => (
              <SelectItem key={campaign.id} value={campaign.id}>
                {campaign.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void handleEnroll()} isLoading={isEnrolling} disabled={!campaignId}>
            Enroll
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
