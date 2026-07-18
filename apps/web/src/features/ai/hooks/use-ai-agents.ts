"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIAgentResponse } from "../types";

export const AI_AGENTS_QUERY_KEY = ["ai", "agents", "list"] as const;

export interface UseAIAgentsReturn {
  agents: AIAgentResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useAIAgents(): UseAIAgentsReturn {
  const result = useQuery({
    queryKey: AI_AGENTS_QUERY_KEY,
    queryFn: ({ signal }) => aiService.getAIAgents(signal),
  });

  return {
    agents: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
