"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { PromptVersionResponse } from "../types";

export const PROMPT_VERSIONS_QUERY_KEY = (templateId: string) =>
  ["ai", "prompt-templates", templateId, "versions"] as const;

export interface UsePromptVersionsReturn {
  versions: PromptVersionResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function usePromptVersions(templateId: string | undefined): UsePromptVersionsReturn {
  const result = useQuery({
    queryKey: PROMPT_VERSIONS_QUERY_KEY(templateId ?? ""),
    queryFn: ({ signal }) => aiService.getPromptVersions(templateId as string, signal),
    enabled: Boolean(templateId),
  });

  return {
    versions: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
