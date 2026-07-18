"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIOutputResponse } from "../types";

function invalidateJobDetail(queryClient: ReturnType<typeof useQueryClient>, output: AIOutputResponse): void {
  void queryClient.invalidateQueries({ queryKey: ["ai", "jobs", "detail", output.job_id] });
}

export interface UseApproveAIOutputReturn {
  approveOutput: (outputId: string) => Promise<AIOutputResponse>;
  isApproving: boolean;
}

export function useApproveAIOutput(): UseApproveAIOutputReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (outputId: string) => aiService.approveAIOutput(outputId),
    onSuccess: (output) => {
      invalidateJobDetail(queryClient, output);
      toast.success("Output approved.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { approveOutput: (outputId) => mutation.mutateAsync(outputId), isApproving: mutation.isPending };
}

export interface UseRejectAIOutputReturn {
  rejectOutput: (outputId: string) => Promise<AIOutputResponse>;
  isRejecting: boolean;
}

export function useRejectAIOutput(): UseRejectAIOutputReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (outputId: string) => aiService.rejectAIOutput(outputId),
    onSuccess: (output) => {
      invalidateJobDetail(queryClient, output);
      toast.success("Output rejected.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { rejectOutput: (outputId) => mutation.mutateAsync(outputId), isRejecting: mutation.isPending };
}
