"use client";

import { forwardRef } from "react";
import { Timeline, TimelineItem } from "@/components/ui/timeline";
import { AlertCircle, CheckCircle2, Circle, Loader2, type IconComponent } from "@/icons";
import { cn } from "@/lib/utils";
import { useAIJob } from "../hooks/use-ai-job";
import { useAIJobStream, useAIJobSteps } from "../hooks/use-ai-job-stream";
import { ACTIVE_JOB_STATUSES } from "../types";

export interface AgentStepDefinition {
  /** Must match the LangGraph node name the backend publishes (see
   * `app/agents/*.py`'s `@step("...")` decorators) — not just a display label. */
  node: string;
  label: string;
}

export interface AgentStepTimelineProps {
  jobId: string | undefined;
  steps: AgentStepDefinition[];
  className?: string;
}

type StepState = "pending" | "in_progress" | "completed" | "failed";

const SpinningLoader: IconComponent = forwardRef<SVGSVGElement, React.ComponentProps<IconComponent>>(
  function SpinningLoader(props, ref) {
    return <Loader2 {...props} ref={ref} className={cn("animate-spin", props.className)} />;
  },
) as IconComponent;

const STATE_META: Record<StepState, { icon: IconComponent; tone: "default" | "info" | "success" | "danger" }> = {
  pending: { icon: Circle, tone: "default" },
  in_progress: { icon: SpinningLoader, tone: "info" },
  completed: { icon: CheckCircle2, tone: "success" },
  failed: { icon: AlertCircle, tone: "danger" },
};

/**
 * Live "agent thinking" step list — reusable across the Research (module
 * 05), Email Generation (module 06), and Reply Analysis (module 09) review
 * screens. Self-contained: opens its own `useAIJobStream` WebSocket (a
 * second mount for the same `jobId` shares TanStack Query's cache, so this
 * is safe to render alongside other job-status consumers) and merges it
 * with `useAIJob`'s polling baseline, so callers just pass a `jobId` and the
 * ordered list of node names/labels for whichever graph is running.
 */
export function AgentStepTimeline({ jobId, steps, className }: AgentStepTimelineProps): React.ReactElement | null {
  const { job } = useAIJob(jobId);
  useAIJobStream(jobId);
  const liveSteps = useAIJobSteps(jobId);

  if (!jobId) return null;

  const jobIsRunning = job ? ACTIVE_JOB_STATUSES.has(job.status) : false;

  function stateFor(node: string): { state: StepState; detail: string | null } {
    const event = liveSteps.find((s) => s.node === node);
    if (event) {
      return {
        state: event.status === "started" ? "in_progress" : event.status,
        detail: event.detail,
      };
    }
    // No live event yet for this node — a client that connects after the
    // job already finished (or one that missed events on a dropped socket,
    // now caught up via useAIJob's polling) still shows a coherent final
    // state instead of stalling on "pending" forever.
    if (job && !jobIsRunning && job.status === "completed") return { state: "completed", detail: null };
    return { state: "pending", detail: null };
  }

  return (
    <Timeline className={className}>
      {steps.map((step, index) => {
        const { state, detail } = stateFor(step.node);
        const meta = STATE_META[state];
        return (
          <TimelineItem
            key={step.node}
            icon={meta.icon}
            tone={meta.tone}
            isLast={index === steps.length - 1}
            title={step.label}
            description={state === "failed" ? detail ?? "This step failed." : undefined}
          />
        );
      })}
    </Timeline>
  );
}
