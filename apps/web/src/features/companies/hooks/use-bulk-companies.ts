"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { BulkActionResponse, BulkCompanyActionRequest } from "../types";

export interface UseBulkCompaniesReturn {
  bulkAction: (payload: BulkCompanyActionRequest) => Promise<BulkActionResponse>;
  isRunning: boolean;
}

export function useBulkCompanies(): UseBulkCompaniesReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: BulkCompanyActionRequest) => companyService.bulkCompanyAction(payload),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
      if (result.failed_count > 0) {
        toast.warning(`${result.success_count} succeeded, ${result.failed_count} failed.`);
      } else {
        toast.success(`${result.success_count} compan${result.success_count === 1 ? "y" : "ies"} updated.`);
      }
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { bulkAction: (payload) => mutation.mutateAsync(payload), isRunning: mutation.isPending };
}
