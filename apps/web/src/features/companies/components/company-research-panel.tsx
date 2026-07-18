"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Timeline, TimelineItem } from "@/components/ui/timeline";
import { AlertTriangle, History, RefreshCw, Sparkles, Target, TrendingUp, Users } from "@/icons";
import { useAIJob } from "@/features/ai/hooks/use-ai-job";
import { ACTIVE_JOB_STATUSES } from "@/features/ai/types";
import { COMPANY_QUERY_KEY } from "../hooks/use-company";
import {
  COMPANY_RESEARCH_HISTORY_QUERY_KEY,
  COMPANY_RESEARCH_QUERY_KEY,
  useCompanyResearch,
  useTriggerCompanyResearch,
} from "../hooks/use-company-research";

export interface CompanyResearchPanelProps {
  companyId: string;
}

const JOB_STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  running: "Researching",
  retrying: "Retrying",
};

export function CompanyResearchPanel({ companyId }: CompanyResearchPanelProps): React.ReactElement {
  const queryClient = useQueryClient();
  const { research, isLoading, isError, errorMessage, refetch } = useCompanyResearch(companyId);
  const { triggerResearch, isTriggering } = useTriggerCompanyResearch();
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);
  const { job } = useAIJob(activeJobId);
  const refreshConfirm = useConfirmDialog();

  const isRunning = job ? ACTIVE_JOB_STATUSES.has(job.status) : false;

  useEffect(() => {
    if (job && !ACTIVE_JOB_STATUSES.has(job.status)) {
      void queryClient.invalidateQueries({ queryKey: COMPANY_RESEARCH_QUERY_KEY(companyId) });
      void queryClient.invalidateQueries({ queryKey: COMPANY_RESEARCH_HISTORY_QUERY_KEY(companyId) });
      void queryClient.invalidateQueries({ queryKey: COMPANY_QUERY_KEY(companyId) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when the polled status changes
  }, [job?.status]);

  async function handleTrigger(force: boolean): Promise<void> {
    const triggered = await triggerResearch({ companyId, force });
    setActiveJobId(triggered.id);
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

  if (isError) {
    return (
      <ErrorState title="Couldn't load research" description={errorMessage ?? undefined} onRetry={refetch} />
    );
  }

  if (!research && !isRunning) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No research yet"
        description="Run AI research to build a structured company profile with pain points and sales opportunities."
        action={
          <Button size="sm" onClick={() => void handleTrigger(false)} isLoading={isTriggering}>
            <Sparkles className="size-4" />
            Research this company
          </Button>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-1">
          {research && !isRunning && (
            <span className="text-body-sm text-muted-foreground">
              Last researched {formatDistanceToNow(new Date(research.researched_at), { addSuffix: true })}
            </span>
          )}
          {isRunning && (
            <div className="flex items-center gap-2">
              <StatusBadge tone="info" pulse>
                {JOB_STATUS_LABEL[job?.status ?? "running"] ?? "Researching"}
              </StatusBadge>
              <span className="text-body-sm text-muted-foreground">This can take up to a minute…</span>
            </div>
          )}
          {job && job.status === "failed" && !isRunning && (
            <span className="text-body-sm text-danger">
              Research failed: {job.error_message ?? "The AI provider request failed."}
            </span>
          )}
        </div>
        <Button
          size="sm"
          variant={research ? "outline" : "primary"}
          onClick={() => (research ? refreshConfirm.open() : void handleTrigger(false))}
          isLoading={isTriggering || isRunning}
        >
          {research ? <RefreshCw className="size-4" /> : <Sparkles className="size-4" />}
          {research ? "Refresh Research" : "Research this Company"}
        </Button>
      </div>

      {research?.data_quality === "llm_knowledge_only" && (
        <Alert variant="warning">
          <AlertTitle>Limited data</AlertTitle>
          <AlertDescription>
            This company&apos;s website couldn&apos;t be reached, so this profile relies on the model&apos;s
            own knowledge instead of the company&apos;s own site content — treat details as directional,
            not verified.
          </AlertDescription>
        </Alert>
      )}

      {research && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {research.summary && (
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-body-sm text-foreground">{research.summary}</p>
              </CardContent>
            </Card>
          )}

          {research.pain_points && research.pain_points.length > 0 && (
            <Card className="border-danger/40 lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-danger">
                  <AlertTriangle className="size-4" />
                  Pain Points
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {research.pain_points.map((point, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-soft/40 p-3"
                  >
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" />
                    <p className="text-body-sm text-foreground">{point}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {research.sales_opportunities && research.sales_opportunities.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="size-4" />
                  Sales Opportunities
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {research.sales_opportunities.map((item, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      • {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {research.growth_signals && research.growth_signals.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="size-4" />
                  Growth Signals
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {research.growth_signals.map((item, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      • {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {research.products_services && research.products_services.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Products & Services</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {research.products_services.map((item, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      • {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {(research.target_customers || research.business_model || research.estimated_revenue || research.funding_stage) && (
            <Card>
              <CardHeader>
                <CardTitle>Business Model</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {research.business_model && (
                  <div>
                    <dt className="text-caption text-muted-foreground">Model</dt>
                    <dd className="text-body-sm text-foreground">{research.business_model}</dd>
                  </div>
                )}
                {research.target_customers && (
                  <div>
                    <dt className="text-caption text-muted-foreground">Target customers</dt>
                    <dd className="text-body-sm text-foreground">{research.target_customers}</dd>
                  </div>
                )}
                {research.estimated_revenue && (
                  <div>
                    <dt className="text-caption text-muted-foreground">Estimated revenue</dt>
                    <dd className="text-body-sm text-foreground">{research.estimated_revenue}</dd>
                  </div>
                )}
                {research.funding_stage && (
                  <div>
                    <dt className="text-caption text-muted-foreground">Funding stage</dt>
                    <dd className="text-body-sm text-foreground">{research.funding_stage}</dd>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {research.technologies && research.technologies.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Technologies</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-1.5">
                {research.technologies.map((tech, index) => (
                  <Badge key={index} variant="soft">
                    {tech}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          )}

          {research.competitors && research.competitors.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="size-4" />
                  Competitors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2">
                  {research.competitors.map((competitor, index) => (
                    <li key={index} className="text-body-sm text-foreground">
                      {competitor}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {research.recent_news && research.recent_news.length > 0 && (
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="size-4" />
                  Recent News
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Timeline>
                  {research.recent_news.map((item, index, all) => (
                    <TimelineItem key={index} icon={History} title={item} isLast={index === all.length - 1} />
                  ))}
                </Timeline>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <ConfirmDialog
        open={refreshConfirm.isOpen}
        onOpenChange={refreshConfirm.onOpenChange}
        title="Refresh research?"
        description="This overwrites the current company profile with a freshly generated one. Only the latest research is kept — previous runs stay visible in the job history."
        confirmLabel="Refresh research"
        confirmVariant="primary"
        isConfirming={isTriggering}
        onConfirm={() => void handleTrigger(true)}
      />
    </div>
  );
}
