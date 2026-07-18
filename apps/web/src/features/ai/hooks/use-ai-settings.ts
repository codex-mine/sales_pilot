"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AISettingsResponse, AISettingsUpdateRequest } from "../types";

export const AI_SETTINGS_QUERY_KEY = ["ai", "settings"] as const;

export interface UseAISettingsReturn {
  settings: AISettingsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useAISettings(): UseAISettingsReturn {
  const result = useQuery({
    queryKey: AI_SETTINGS_QUERY_KEY,
    queryFn: ({ signal }) => aiService.getAISettings(signal),
  });

  return {
    settings: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}

export interface UseUpdateAISettingsReturn {
  updateSettings: (payload: AISettingsUpdateRequest) => Promise<AISettingsResponse>;
  isUpdating: boolean;
}

export function useUpdateAISettings(): UseUpdateAISettingsReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: AISettingsUpdateRequest) => aiService.updateAISettings(payload),
    onSuccess: (settings, payload) => {
      queryClient.setQueryData(AI_SETTINGS_QUERY_KEY, settings);
      toast.success(payload.remove ? "Provider credentials removed." : "Provider credentials saved.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateSettings: (payload) => mutation.mutateAsync(payload), isUpdating: mutation.isPending };
}
