"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompaniesQuery } from "../types";

export interface UseExportCompaniesReturn {
  exportCompanies: (query?: CompaniesQuery & { company_ids?: string[] }) => Promise<void>;
  isExporting: boolean;
}

export function useExportCompanies(): UseExportCompaniesReturn {
  const mutation = useMutation({
    mutationFn: (query: (CompaniesQuery & { company_ids?: string[] }) | undefined) =>
      companyService.exportCompanies(query ?? {}),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("Export downloaded.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    exportCompanies: (query) => mutation.mutateAsync(query).then(() => undefined),
    isExporting: mutation.isPending,
  };
}
