"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { emailTemplateService } from "../services/email-template.service";
import type { EmailTemplateResponse, EmailTemplatesQuery, PaginationMeta } from "../types";

export const EMAIL_TEMPLATES_QUERY_KEY = (query: EmailTemplatesQuery) => ["email-templates", "list", query] as const;
export const EMAIL_TEMPLATE_QUERY_KEY = (templateId: string) => ["email-templates", "detail", templateId] as const;

export interface UseEmailTemplatesReturn {
  templates: EmailTemplateResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useEmailTemplates(query: EmailTemplatesQuery = {}): UseEmailTemplatesReturn {
  const result = useQuery({
    queryKey: EMAIL_TEMPLATES_QUERY_KEY(query),
    queryFn: ({ signal }) => emailTemplateService.getEmailTemplates(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    templates: result.data?.templates ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseEmailTemplateReturn {
  template: EmailTemplateResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useEmailTemplate(templateId: string): UseEmailTemplateReturn {
  const result = useQuery({
    queryKey: EMAIL_TEMPLATE_QUERY_KEY(templateId),
    queryFn: ({ signal }) => emailTemplateService.getEmailTemplate(templateId, signal),
    enabled: Boolean(templateId),
  });

  return {
    template: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
