"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { ImportPreviewResponse, ImportResultResponse, LeadsQuery } from "../types";

export interface UseImportLeadsReturn {
  previewImport: (file: File) => Promise<ImportPreviewResponse>;
  isPreviewing: boolean;
  commitImport: (args: { file: File; mapping: Record<string, string> }) => Promise<ImportResultResponse>;
  isCommitting: boolean;
}

/** Two-step, stateless-on-the-server import flow (see backend's LeadImportExportService docstring): preview parses + suggests a mapping without persisting anything; commit re-submits the same file with the confirmed mapping. */
export function useImportLeads(): UseImportLeadsReturn {
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: (file: File) => leadService.previewImport(file),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const commitMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: Record<string, string> }) =>
      leadService.commitImport(file, mapping),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      toast.success(`Imported ${result.successful_count} of ${result.total_rows} leads.`);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    previewImport: (file) => previewMutation.mutateAsync(file),
    isPreviewing: previewMutation.isPending,
    commitImport: (args) => commitMutation.mutateAsync(args),
    isCommitting: commitMutation.isPending,
  };
}

export interface UseExportLeadsReturn {
  exportLeads: (query?: LeadsQuery & { lead_ids?: string[] }) => Promise<void>;
  isExporting: boolean;
}

export function useExportLeads(): UseExportLeadsReturn {
  const mutation = useMutation({
    mutationFn: (query: (LeadsQuery & { lead_ids?: string[] }) | undefined) => leadService.exportLeads(query ?? {}),
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
    exportLeads: (query) => mutation.mutateAsync(query).then(() => undefined),
    isExporting: mutation.isPending,
  };
}
