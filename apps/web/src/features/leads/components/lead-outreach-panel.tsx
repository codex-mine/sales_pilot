"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Sparkles } from "@/icons";
import { AI_JOB_QUERY_KEY, useAIJob } from "@/features/ai/hooks/use-ai-job";
import { ACTIVE_JOB_STATUSES } from "@/features/ai/types";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { EmailDraftCard } from "./email-draft-card";
import { EmailVariantCard } from "./email-variant-card";
import {
  LEAD_EMAIL_DRAFTS_QUERY_KEY,
  useGenerateLeadEmail,
  useLeadEmailDrafts,
} from "../hooks/use-lead-email-generation";
import {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateType,
  type EmailTone,
} from "../types";

export interface LeadOutreachPanelProps {
  leadId: string;
}

const JOB_STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  running: "Writing your email",
  retrying: "Retrying",
};

export function LeadOutreachPanel({ leadId }: LeadOutreachPanelProps): React.ReactElement {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { drafts, isLoading, isError, errorMessage, refetch } = useLeadEmailDrafts(leadId);
  const { generateEmail, isGenerating } = useGenerateLeadEmail();

  const [templateType, setTemplateType] = useState<EmailTemplateType>("cold_outreach");
  const [tone, setTone] = useState<EmailTone>("professional");
  const [customInstruction, setCustomInstruction] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);
  const { job } = useAIJob(activeJobId);

  const isRunning = job ? ACTIVE_JOB_STATUSES.has(job.status) : false;

  useEffect(() => {
    if (job && !ACTIVE_JOB_STATUSES.has(job.status)) {
      void queryClient.invalidateQueries({ queryKey: LEAD_EMAIL_DRAFTS_QUERY_KEY(leadId) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when the polled status changes
  }, [job?.status]);

  async function handleGenerate(): Promise<void> {
    const triggered = await generateEmail({
      leadId,
      payload: { template_type: templateType, tone, custom_instruction: customInstruction || undefined, variant_count: 2 },
    });
    setActiveJobId(triggered.id);
  }

  const pendingVariants = (job?.outputs ?? []).filter(
    (output) => output.output_type === "email_variant" && output.is_approved === null,
  );

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError) {
    return <ErrorState title="Couldn't load outreach" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="size-4" />
            Generate a personalized email
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label required>Template type</Label>
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
              <Label required>Tone</Label>
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
          <div className="flex flex-col gap-1.5">
            <Label>Additional instruction (optional)</Label>
            <Textarea
              rows={2}
              placeholder="e.g. mention we work with similar SaaS companies"
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={() => void handleGenerate()} isLoading={isGenerating || isRunning} disabled={isRunning}>
              <Sparkles className="size-4" />
              Generate Email
            </Button>
            {isRunning && (
              <StatusBadge tone="info" pulse>
                {JOB_STATUS_LABEL[job?.status ?? "running"] ?? "Working"}
              </StatusBadge>
            )}
            {job && job.status === "failed" && !isRunning && (
              <span className="text-body-sm text-danger">{job.error_message ?? "Generation failed."}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {pendingVariants.length > 0 && (
        <div className="flex flex-col gap-4">
          <h3 className="text-body-md font-semibold text-foreground">
            Review {pendingVariants.length} variant{pendingVariants.length === 1 ? "" : "s"}
          </h3>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {pendingVariants.map((output) => (
              <EmailVariantCard
                key={output.id}
                leadId={leadId}
                jobId={job!.id}
                output={output}
                defaultFromEmail={user?.email ?? ""}
                defaultFromName={user?.full_name ?? ""}
                onApproved={() => void queryClient.invalidateQueries({ queryKey: AI_JOB_QUERY_KEY(job!.id) })}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-4">
        <h3 className="text-body-md font-semibold text-foreground">Emails</h3>
        {drafts.length === 0 ? (
          <EmptyState
            icon={Mail}
            title="No emails yet"
            description="Approve a generated variant to create a ready-to-send draft here."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {drafts.map((email) => (
              <EmailDraftCard key={email.id} leadId={leadId} email={email} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
