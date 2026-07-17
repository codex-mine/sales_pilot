"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { BulkActionResponse, BulkLeadActionRequest } from "../types";

export interface UseBulkLeadsReturn {
  bulkAction: (payload: BulkLeadActionRequest) => Promise<BulkActionResponse>;
  isRunning: boolean;
}

export function useBulkLeads(): UseBulkLeadsReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: BulkLeadActionRequest) => leadService.bulkLeadAction(payload),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      if (result.failed_count > 0) {
        toast.warning(`${result.success_count} succeeded, ${result.failed_count} failed.`);
      } else {
        toast.success(`${result.success_count} lead${result.success_count === 1 ? "" : "s"} updated.`);
      }
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { bulkAction: (payload) => mutation.mutateAsync(payload), isRunning: mutation.isPending };
}
