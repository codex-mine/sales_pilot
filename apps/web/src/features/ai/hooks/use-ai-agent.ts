"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIAgentResponse } from "../types";

export const AI_AGENT_QUERY_KEY = (agentId: string) => ["ai", "agents", "detail", agentId] as const;

export interface UseAIAgentReturn {
  agent: AIAgentResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useAIAgent(agentId: string | undefined): UseAIAgentReturn {
  const result = useQuery({
    queryKey: AI_AGENT_QUERY_KEY(agentId ?? ""),
    queryFn: ({ signal }) => aiService.getAIAgent(agentId as string, signal),
    enabled: Boolean(agentId),
  });

  return {
    agent: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
