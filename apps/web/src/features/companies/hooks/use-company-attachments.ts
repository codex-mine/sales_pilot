"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyAttachmentResponse } from "../types";
import { COMPANY_QUERY_KEY } from "./use-company";

const ATTACHMENTS_QUERY_KEY = (companyId: string) => ["companies", "attachments", companyId] as const;

export interface UseCompanyAttachmentsReturn {
  attachments: CompanyAttachmentResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  uploadAttachment: (file: File) => void;
  isUploading: boolean;
  deleteAttachment: (attachmentId: string) => void;
  isDeleting: boolean;
}

export function useCompanyAttachments(companyId: string): UseCompanyAttachmentsReturn {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ATTACHMENTS_QUERY_KEY(companyId),
    queryFn: () => companyService.getCompanyAttachments(companyId),
    enabled: Boolean(companyId),
  });

  function invalidate(): void {
    void queryClient.invalidateQueries({ queryKey: ATTACHMENTS_QUERY_KEY(companyId) });
    void queryClient.invalidateQueries({ queryKey: COMPANY_QUERY_KEY(companyId) });
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => companyService.uploadCompanyAttachment(companyId, file),
    onSuccess: () => {
      toast.success("Attachment uploaded.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (attachmentId: string) => companyService.deleteCompanyAttachment(companyId, attachmentId),
    onSuccess: () => {
      toast.success("Attachment deleted.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    attachments: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
    uploadAttachment: (file) => uploadMutation.mutate(file),
    isUploading: uploadMutation.isPending,
    deleteAttachment: (attachmentId) => deleteMutation.mutate(attachmentId),
    isDeleting: deleteMutation.isPending,
  };
}
