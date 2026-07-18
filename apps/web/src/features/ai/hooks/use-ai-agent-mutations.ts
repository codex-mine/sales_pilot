"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIAgentCreateRequest, AIAgentResponse, AIAgentUpdateRequest } from "../types";
import { AI_AGENTS_QUERY_KEY } from "./use-ai-agents";
import { AI_AGENT_QUERY_KEY } from "./use-ai-agent";

export interface UseCreateAIAgentReturn {
  createAgent: (payload: AIAgentCreateRequest) => Promise<AIAgentResponse>;
  isCreating: boolean;
}

export function useCreateAIAgent(): UseCreateAIAgentReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: AIAgentCreateRequest) => aiService.createAIAgent(payload),
    onSuccess: () => {
      toast.success("AI agent created.");
      void queryClient.invalidateQueries({ queryKey: AI_AGENTS_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createAgent: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateAIAgentReturn {
  updateAgent: (args: { agentId: string; payload: AIAgentUpdateRequest }) => Promise<AIAgentResponse>;
  isUpdating: boolean;
}

export function useUpdateAIAgent(): UseUpdateAIAgentReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ agentId, payload }: { agentId: string; payload: AIAgentUpdateRequest }) =>
      aiService.updateAIAgent(agentId, payload),
    onSuccess: (agent) => {
      queryClient.setQueryData(AI_AGENT_QUERY_KEY(agent.id), agent);
      void queryClient.invalidateQueries({ queryKey: AI_AGENTS_QUERY_KEY });
      toast.success("AI agent updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateAgent: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteAIAgentReturn {
  deleteAgent: (agentId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteAIAgent(): UseDeleteAIAgentReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (agentId: string) => aiService.deleteAIAgent(agentId),
    onSuccess: () => {
      toast.success("AI agent deleted.");
      void queryClient.invalidateQueries({ queryKey: AI_AGENTS_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteAgent: (agentId) => mutation.mutateAsync(agentId), isDeleting: mutation.isPending };
}
