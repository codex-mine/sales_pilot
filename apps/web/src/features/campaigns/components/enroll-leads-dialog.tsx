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
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { useLeads } from "@/features/leads/hooks/use-leads";
import { useBulkEnrollLeads } from "../hooks/use-campaign-enrollment";

export interface EnrollLeadsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  campaignId: string;
}

/** Picks from the org's active (non-archived) leads and bulk-enrolls the
 * selection into this campaign's active sequence. */
export function EnrollLeadsDialog({ open, onOpenChange, campaignId }: EnrollLeadsDialogProps): React.ReactElement {
  const [leadIds, setLeadIds] = useState<string[]>([]);
  const { leads, isLoading } = useLeads({ page_size: 500, archived: false });
  const { bulkEnroll, isEnrolling } = useBulkEnrollLeads();

  const options: MultiSelectOption[] = leads.map((lead) => ({
    value: lead.id,
    label: lead.company_name ? `${lead.full_name} (${lead.company_name})` : lead.full_name,
  }));

  async function handleEnroll(): Promise<void> {
    if (leadIds.length === 0) return;
    await bulkEnroll({ campaignId, payload: { lead_ids: leadIds } });
    setLeadIds([]);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enroll leads</DialogTitle>
          <DialogDescription>Add leads to this campaign&apos;s active sequence.</DialogDescription>
        </DialogHeader>
        <MultiSelect
          options={options}
          values={leadIds}
          onValuesChange={setLeadIds}
          placeholder="Select leads..."
          disabled={isLoading}
        />
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => void handleEnroll()}
            isLoading={isEnrolling}
            disabled={leadIds.length === 0}
          >
            Enroll {leadIds.length > 0 ? leadIds.length : ""} lead{leadIds.length === 1 ? "" : "s"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
