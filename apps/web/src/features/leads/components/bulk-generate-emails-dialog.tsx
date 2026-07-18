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
import {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateType,
  type EmailTone,
} from "../types";

export interface BulkGenerateEmailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadCount: number;
  isGenerating: boolean;
  onGenerate: (args: { templateType: EmailTemplateType; tone: EmailTone }) => Promise<void>;
}

/** Collects the one required choice (tone + type) bulk generation needs
 * before fanning out — each lead still gets its own individually-approvable
 * variants afterward, reviewed one at a time on its own Outreach tab. */
export function BulkGenerateEmailsDialog({
  open,
  onOpenChange,
  leadCount,
  isGenerating,
  onGenerate,
}: BulkGenerateEmailsDialogProps): React.ReactElement {
  const [templateType, setTemplateType] = useState<EmailTemplateType>("cold_outreach");
  const [tone, setTone] = useState<EmailTone>("professional");

  async function handleGenerate(): Promise<void> {
    await onGenerate({ templateType, tone });
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Generate emails for {leadCount} lead(s)</DialogTitle>
          <DialogDescription>
            Each lead&apos;s email is generated and reviewed individually — nothing is sent automatically.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Select value={templateType} onValueChange={(v) => setTemplateType(v as EmailTemplateType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EMAIL_TEMPLATE_TYPE_CHOICES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {EMAIL_TEMPLATE_TYPE_LABELS[type]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Select value={tone} onValueChange={(v) => setTone(v as EmailTone)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EMAIL_TONE_CHOICES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {EMAIL_TONE_LABELS[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void handleGenerate()} isLoading={isGenerating}>
            Generate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
