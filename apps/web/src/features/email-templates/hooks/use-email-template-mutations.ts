"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { emailTemplateService } from "../services/email-template.service";
import type { EmailTemplateResponse, EmailTemplateUpdateRequest } from "../types";
import { EMAIL_TEMPLATE_QUERY_KEY } from "./use-email-templates";

export interface UseUpdateEmailTemplateReturn {
  updateTemplate: (args: { templateId: string; payload: EmailTemplateUpdateRequest }) => Promise<EmailTemplateResponse>;
  isUpdating: boolean;
}

export function useUpdateEmailTemplate(): UseUpdateEmailTemplateReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ templateId, payload }: { templateId: string; payload: EmailTemplateUpdateRequest }) =>
      emailTemplateService.updateEmailTemplate(templateId, payload),
    onSuccess: (template) => {
      queryClient.setQueryData(EMAIL_TEMPLATE_QUERY_KEY(template.id), template);
      void queryClient.invalidateQueries({ queryKey: ["email-templates", "list"] });
      toast.success("Email template updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { updateTemplate: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteEmailTemplateReturn {
  deleteTemplate: (templateId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteEmailTemplate(): UseDeleteEmailTemplateReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (templateId: string) => emailTemplateService.deleteEmailTemplate(templateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["email-templates", "list"] });
      toast.success("Email template deleted.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { deleteTemplate: (templateId) => mutation.mutateAsync(templateId), isDeleting: mutation.isPending };
}
