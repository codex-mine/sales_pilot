"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { AttachmentResponse } from "../types";
import { LEAD_QUERY_KEY } from "./use-lead";

const ATTACHMENTS_QUERY_KEY = (leadId: string) => ["leads", "attachments", leadId] as const;

export interface UseLeadAttachmentsReturn {
  attachments: AttachmentResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  uploadAttachment: (file: File) => void;
  isUploading: boolean;
  deleteAttachment: (attachmentId: string) => void;
  isDeleting: boolean;
}

export function useLeadAttachments(leadId: string): UseLeadAttachmentsReturn {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ATTACHMENTS_QUERY_KEY(leadId),
    queryFn: () => leadService.getAttachments(leadId),
    enabled: Boolean(leadId),
  });

  function invalidate(): void {
    void queryClient.invalidateQueries({ queryKey: ATTACHMENTS_QUERY_KEY(leadId) });
    void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => leadService.uploadAttachment(leadId, file),
    onSuccess: () => {
      toast.success("Attachment uploaded.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (attachmentId: string) => leadService.deleteAttachment(leadId, attachmentId),
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
