"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getInMemoryAccessToken, WS_BASE_URL } from "@/lib/api/client";
import { AI_JOB_QUERY_KEY } from "./use-ai-job";
import type { AIJobResponse } from "../types";

export interface AIJobStepEvent {
  node: string;
  status: "started" | "completed" | "failed";
  detail: string | null;
  timestamp: string;
}

export const AI_JOB_STEPS_QUERY_KEY = (jobId: string) => ["ai", "jobs", "steps", jobId] as const;

type IncomingMessage =
  | { type: "job_state"; job: AIJobResponse }
  | { type: "job_terminal"; job: AIJobResponse }
  | { type: "step"; event: AIJobStepEvent };

function mergeStepEvent(existing: AIJobStepEvent[] | undefined, event: AIJobStepEvent): AIJobStepEvent[] {
  const steps = existing ? [...existing] : [];
  const index = steps.findIndex((s) => s.node === event.node);
  if (index >= 0) steps[index] = event;
  else steps.push(event);
  return steps;
}

/**
 * Layers live WebSocket step/status updates onto the same TanStack Query
 * cache key `useAIJob` (module 04's polling hook) already reads
 * (`AI_JOB_QUERY_KEY`) — both mechanisms run together, call both in any
 * component showing live job status: `useAIJob` establishes and refetches
 * baseline truth via polling, this hook just makes updates arrive sooner by
 * pushing the same full `AIJobResponse` shape the polling fetch would
 * eventually see (`job_state`/`job_terminal` messages), so writing it
 * straight into the cache is a full, safe replacement rather than a partial
 * merge that could clobber fields. Per-step progress (`step` messages) has
 * no equivalent field on `AIJobResponse` to merge into, so it's tracked in
 * its own cache key instead (see `useAIJobSteps`).
 *
 * On any socket error or early close, this silently stops — `useAIJob`'s
 * polling, already running alongside it, keeps the UI correct without ever
 * surfacing the drop as a user-facing error.
 */
export function useAIJobStream(jobId: string | undefined): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!jobId) return;

    const token = getInMemoryAccessToken();
    const url = `${WS_BASE_URL}/ws/ai-jobs/${jobId}${token ? `?token=${encodeURIComponent(token)}` : ""}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (error) {
      console.warn("Failed to open AI job stream; relying on polling.", error);
      return;
    }

    ws.onmessage = (event) => {
      let data: IncomingMessage;
      try {
        data = JSON.parse(event.data as string) as IncomingMessage;
      } catch {
        return;
      }
      if (data.type === "job_state" || data.type === "job_terminal") {
        queryClient.setQueryData(AI_JOB_QUERY_KEY(jobId), data.job);
      } else if (data.type === "step") {
        queryClient.setQueryData(AI_JOB_STEPS_QUERY_KEY(jobId), (old: AIJobStepEvent[] | undefined) =>
          mergeStepEvent(old, data.event),
        );
      }
    };

    ws.onerror = (error) => {
      console.warn("AI job stream error; relying on polling.", error);
    };

    return () => ws.close();
  }, [jobId, queryClient]);
}

/** Reads the live step list `useAIJobStream` writes into the cache — a pure
 * cache subscription (`enabled: false`, nothing ever fetched over HTTP for
 * this key), so it re-renders whenever a new `step` message lands. */
export function useAIJobSteps(jobId: string | undefined): AIJobStepEvent[] {
  const result = useQuery<AIJobStepEvent[]>({
    queryKey: AI_JOB_STEPS_QUERY_KEY(jobId ?? ""),
    queryFn: () => [],
    enabled: false,
    initialData: [],
  });
  return result.data ?? [];
}
