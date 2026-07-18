"use client";

import { formatDistanceToNow } from "date-fns";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { AlertTriangle, CheckCircle2, RotateCcw, XCircle } from "@/icons";
import { formatCurrency } from "@/lib/utils";
import { useAIJob } from "../hooks/use-ai-job";
import { useRetryAIJob } from "../hooks/use-ai-job-mutations";
import { useApproveAIOutput, useRejectAIOutput } from "../hooks/use-ai-output-mutations";
import { ACTIVE_JOB_STATUSES } from "../types";

export interface AIJobDetailDrawerProps {
  jobId: string | undefined;
  onOpenChange: (open: boolean) => void;
}

/** Full job detail: rendered input, per-output content with approve/reject, error/retry for failures. Polls live via useAIJob while the job is in flight. */
export function AIJobDetailDrawer({ jobId, onOpenChange }: AIJobDetailDrawerProps): React.ReactElement {
  const { job, isLoading } = useAIJob(jobId);
  const { retryJob, isRetrying } = useRetryAIJob();
  const { approveOutput, isApproving } = useApproveAIOutput();
  const { rejectOutput, isRejecting } = useRejectAIOutput();

  const isRunning = job ? ACTIVE_JOB_STATUSES.has(job.status) : false;

  return (
    <Drawer open={Boolean(jobId)} onOpenChange={onOpenChange}>
      <DrawerContent className="max-w-2xl">
        <DrawerHeader>
          <DrawerTitle className="flex items-center gap-2">
            {job?.job_type ?? "AI job"}
            {job && (
              <StatusBadge
                tone={
                  job.status === "completed"
                    ? "success"
                    : job.status === "failed"
                      ? "danger"
                      : job.status === "cancelled"
                        ? "neutral"
                        : "info"
                }
                pulse={isRunning}
              >
                {job.status}
              </StatusBadge>
            )}
          </DrawerTitle>
          <DrawerDescription>
            {job && `Started ${formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}`}
          </DrawerDescription>
        </DrawerHeader>

        <div className="flex flex-1 flex-col gap-6 overflow-y-auto">
          {isLoading || !job ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-48 w-full" />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 text-body-sm sm:grid-cols-3">
                <div>
                  <p className="text-caption text-muted-foreground">Provider / model</p>
                  <p className="text-foreground">{job.provider ?? "—"} · {job.model_name ?? "—"}</p>
                </div>
                <div>
                  <p className="text-caption text-muted-foreground">Tokens</p>
                  <p className="text-foreground">{job.total_tokens?.toLocaleString() ?? "—"}</p>
                </div>
                <div>
                  <p className="text-caption text-muted-foreground">Cost</p>
                  <p className="text-foreground">{job.cost_usd != null ? formatCurrency(job.cost_usd) : "—"}</p>
                </div>
                <div>
                  <p className="text-caption text-muted-foreground">Latency</p>
                  <p className="text-foreground">{job.latency_ms != null ? `${job.latency_ms}ms` : "—"}</p>
                </div>
                <div>
                  <p className="text-caption text-muted-foreground">Retries</p>
                  <p className="text-foreground">{job.retry_count} / {job.max_retries}</p>
                </div>
                {job.parent_job_id && (
                  <div>
                    <p className="text-caption text-muted-foreground">Retried from</p>
                    <p className="truncate text-foreground">{job.parent_job_id}</p>
                  </div>
                )}
              </div>

              {job.status === "failed" && (
                <Alert variant="danger">
                  <AlertTriangle className="size-4" />
                  <AlertTitle>Job failed</AlertTitle>
                  <AlertDescription className="flex flex-col gap-3">
                    <p>{job.error_message}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      isLoading={isRetrying}
                      onClick={() => retryJob(job.id)}
                    >
                      <RotateCcw className="size-4" />
                      Retry as new job
                    </Button>
                  </AlertDescription>
                </Alert>
              )}

              {job.input_data && (
                <div className="flex flex-col gap-2">
                  <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
                    Input (rendered prompt)
                  </p>
                  <pre className="max-h-64 overflow-auto rounded-lg bg-muted p-3 text-caption text-foreground">
                    {JSON.stringify(job.input_data, null, 2)}
                  </pre>
                </div>
              )}

              {job.outputs.length > 0 && (
                <div className="flex flex-col gap-3">
                  <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
                    Output{job.outputs.length > 1 ? "s" : ""}
                  </p>
                  {job.outputs.map((output) => (
                    <div key={output.id} className="flex flex-col gap-2 rounded-lg border border-border p-3">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" size="sm">
                          {output.output_type}
                        </Badge>
                        {output.is_approved === true && <Badge variant="success" size="sm">Approved</Badge>}
                        {output.is_approved === false && <Badge variant="danger" size="sm">Rejected</Badge>}
                        {output.is_approved === null && <Badge variant="warning" size="sm">Pending review</Badge>}
                      </div>
                      <p className="whitespace-pre-wrap text-body-sm text-foreground">{output.content_text}</p>
                      {output.is_approved === null && (
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            isLoading={isApproving}
                            onClick={() => approveOutput(output.id)}
                          >
                            <CheckCircle2 className="size-4" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            isLoading={isRejecting}
                            onClick={() => rejectOutput(output.id)}
                          >
                            <XCircle className="size-4" />
                            Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}
