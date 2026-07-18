"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { PromptTemplateResponse } from "../types";

export const PROMPT_TEMPLATES_QUERY_KEY = ["ai", "prompt-templates", "list"] as const;

export interface UsePromptTemplatesReturn {
  templates: PromptTemplateResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function usePromptTemplates(): UsePromptTemplatesReturn {
  const result = useQuery({
    queryKey: PROMPT_TEMPLATES_QUERY_KEY,
    queryFn: ({ signal }) => aiService.getPromptTemplates(signal),
  });

  return {
    templates: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
