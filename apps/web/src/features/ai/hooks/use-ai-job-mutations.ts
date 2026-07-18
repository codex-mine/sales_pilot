"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIJobResponse } from "../types";
import { AI_JOB_QUERY_KEY } from "./use-ai-job";

export interface UseRetryAIJobReturn {
  retryJob: (jobId: string) => Promise<AIJobResponse>;
  isRetrying: boolean;
}

export function useRetryAIJob(): UseRetryAIJobReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (jobId: string) => aiService.retryAIJob(jobId),
    onSuccess: (newJob) => {
      queryClient.setQueryData(AI_JOB_QUERY_KEY(newJob.id), newJob);
      void queryClient.invalidateQueries({ queryKey: ["ai", "jobs", "list"] });
      toast.success("Retry started as a new job.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { retryJob: (jobId) => mutation.mutateAsync(jobId), isRetrying: mutation.isPending };
}

export interface UseCancelAIJobReturn {
  cancelJob: (jobId: string) => Promise<AIJobResponse>;
  isCancelling: boolean;
}

export function useCancelAIJob(): UseCancelAIJobReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (jobId: string) => aiService.cancelAIJob(jobId),
    onSuccess: (job) => {
      queryClient.setQueryData(AI_JOB_QUERY_KEY(job.id), job);
      void queryClient.invalidateQueries({ queryKey: ["ai", "jobs", "list"] });
      toast.success("Job cancelled.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { cancelJob: (jobId) => mutation.mutateAsync(jobId), isCancelling: mutation.isPending };
}
