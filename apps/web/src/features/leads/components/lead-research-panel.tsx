"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { AlertCircle, Clock3, Flag, Send, Shield, Sparkles, Zap } from "@/icons";
import { COMPANY_QUERY_KEY } from "@/features/companies/hooks/use-company";
import { COMPANY_RESEARCH_QUERY_KEY } from "@/features/companies/hooks/use-company-research";
import {
  LEAD_RESEARCH_QUERY_KEY,
  PROSPECT_ANALYSIS_QUERY_KEY,
  useLeadResearch,
  useProspectAnalysis,
  useTriggerLeadResearch,
} from "../hooks/use-lead-research";
import { BUYING_INTENT_LABELS, DECISION_AUTHORITY_LABELS, type BuyingIntent, type DecisionAuthority } from "../types";
import { LEAD_QUERY_KEY } from "../hooks/use-lead";

export interface LeadResearchPanelProps {
  leadId: string;
}

const BUYING_INTENT_TONE: Record<BuyingIntent, "success" | "warning" | "neutral"> = {
  high: "success",
  medium: "warning",
  low: "neutral",
};

const DECISION_AUTHORITY_TONE: Record<DecisionAuthority, "primary" | "info" | "neutral"> = {
  decision_maker: "primary",
  influencer: "info",
  evaluator: "neutral",
  end_user: "neutral",
};

export function LeadResearchPanel({ leadId }: LeadResearchPanelProps): React.ReactElement {
  const queryClient = useQueryClient();
  const { status, isLoading, isError, errorMessage, isRunning, refetch } = useLeadResearch(leadId);
  const { analysis } = useProspectAnalysis(leadId);
  const { triggerResearch, isTriggering } = useTriggerLeadResearch();
  const refreshConfirm = useConfirmDialog();
  // LeadResponse doesn't expose company_id directly — the linked company's id
  // (when this lead's research chained through company research) is only
  // available via the company job this endpoint already returns.
  const companyId = status?.company_job?.entity_id ?? null;

  useEffect(() => {
    if (!isRunning && status) {
      void queryClient.invalidateQueries({ queryKey: PROSPECT_ANALYSIS_QUERY_KEY(leadId) });
      void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
      if (companyId) {
        void queryClient.invalidateQueries({ queryKey: COMPANY_RESEARCH_QUERY_KEY(companyId) });
        void queryClient.invalidateQueries({ queryKey: COMPANY_QUERY_KEY(companyId) });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when the polled status changes
  }, [isRunning]);

  async function handleTrigger(force: boolean): Promise<void> {
    await triggerResearch({ leadId, force });
    void queryClient.invalidateQueries({ queryKey: LEAD_RESEARCH_QUERY_KEY(leadId) });
    refreshConfirm.close();
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !status) {
    return (
      <ErrorState title="Couldn't load research" description={errorMessage ?? undefined} onRetry={refetch} />
    );
  }

  if (!analysis && !isRunning) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No research yet"
        description="Run AI research to score buying intent, surface likely objections, and get a recommended approach for this lead."
        action={
          <Button size="sm" onClick={() => void handleTrigger(false)} isLoading={isTriggering}>
            <Sparkles className="size-4" />
            Research this lead
          </Button>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-2">
          {isRunning ? (
            <>
              <StatusBadge tone="info" pulse>
                {status.company_job && status.company_job.status !== "completed"
                  ? "Researching company"
                  : "Analyzing prospect"}
              </StatusBadge>
              <span className="text-body-sm text-muted-foreground">This can take up to a minute…</span>
            </>
          ) : status.prospect_job?.status === "failed" ? (
            <span className="text-body-sm text-danger">
              Analysis failed: {status.prospect_job.error_message ?? "The AI provider request failed."}
            </span>
          ) : (
            analysis && <span className="text-body-sm text-muted-foreground">Analysis complete.</span>
          )}
        </div>
        <Button
          size="sm"
          variant={analysis ? "outline" : "primary"}
          onClick={() => (analysis ? refreshConfirm.open() : void handleTrigger(false))}
          isLoading={isTriggering || isRunning}
        >
          <Sparkles className="size-4" />
          {analysis ? "Refresh Research" : "Research this Lead"}
        </Button>
      </div>

      {analysis && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Buying Intent</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              {analysis.buying_intent && (
                <StatusBadge tone={BUYING_INTENT_TONE[analysis.buying_intent]}>
                  {BUYING_INTENT_LABELS[analysis.buying_intent]}
                </StatusBadge>
              )}
              {analysis.priority_score != null && (
                <span className="text-body-sm text-muted-foreground">
                  Priority score: <span className="font-medium text-foreground">{analysis.priority_score}</span>
                </span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="size-4" />
                Decision Authority
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              {analysis.decision_authority ? (
                <StatusBadge tone={DECISION_AUTHORITY_TONE[analysis.decision_authority]}>
                  {DECISION_AUTHORITY_LABELS[analysis.decision_authority]}
                </StatusBadge>
              ) : (
                <span className="text-body-sm text-muted-foreground">Unknown</span>
              )}
              {analysis.best_contact_time && (
                <span className="flex items-center gap-1 text-body-sm text-muted-foreground">
                  <Clock3 className="size-3.5" />
                  {analysis.best_contact_time}
                </span>
              )}
            </CardContent>
          </Card>

          {analysis.recommended_approach && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Send className="size-4" />
                  Recommended Approach
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-body-sm text-foreground">{analysis.recommended_approach}</p>
              </CardContent>
            </Card>
          )}

          {analysis.value_proposition && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="size-4" />
                  Value Proposition
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-body-sm text-foreground">{analysis.value_proposition}</p>
              </CardContent>
            </Card>
          )}

          {analysis.predicted_objections && analysis.predicted_objections.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="size-4" />
                  Predicted Objections
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {analysis.predicted_objections.map((item, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      • {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {analysis.likely_goals && analysis.likely_goals.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Flag className="size-4" />
                  Likely Goals
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {analysis.likely_goals.map((item, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      • {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <ConfirmDialog
        open={refreshConfirm.isOpen}
        onOpenChange={refreshConfirm.onOpenChange}
        title="Refresh research?"
        description="This overwrites the current analysis with a freshly generated one. Only the latest analysis is kept — previous runs stay visible in the job history."
        confirmLabel="Refresh research"
        confirmVariant="primary"
        isConfirming={isTriggering}
        onConfirm={() => void handleTrigger(true)}
      />
    </div>
  );
}
