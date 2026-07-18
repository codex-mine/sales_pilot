"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type {
  PromptTemplateCreateRequest,
  PromptTemplateResponse,
  PromptTemplateUpdateRequest,
  PromptVersionCreateRequest,
  PromptVersionResponse,
} from "../types";
import { PROMPT_TEMPLATES_QUERY_KEY } from "./use-prompt-templates";
import { PROMPT_VERSIONS_QUERY_KEY } from "./use-prompt-versions";

export interface UseCreatePromptTemplateReturn {
  createTemplate: (payload: PromptTemplateCreateRequest) => Promise<PromptTemplateResponse>;
  isCreating: boolean;
}

export function useCreatePromptTemplate(): UseCreatePromptTemplateReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: PromptTemplateCreateRequest) => aiService.createPromptTemplate(payload),
    onSuccess: () => {
      toast.success("Prompt template created.");
      void queryClient.invalidateQueries({ queryKey: PROMPT_TEMPLATES_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createTemplate: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdatePromptTemplateReturn {
  updateTemplate: (args: { templateId: string; payload: PromptTemplateUpdateRequest }) => Promise<PromptTemplateResponse>;
  isUpdating: boolean;
}

export function useUpdatePromptTemplate(): UseUpdatePromptTemplateReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ templateId, payload }: { templateId: string; payload: PromptTemplateUpdateRequest }) =>
      aiService.updatePromptTemplate(templateId, payload),
    onSuccess: () => {
      toast.success("Prompt template updated.");
      void queryClient.invalidateQueries({ queryKey: PROMPT_TEMPLATES_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateTemplate: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseCreatePromptVersionReturn {
  createVersion: (args: { templateId: string; payload: PromptVersionCreateRequest }) => Promise<PromptVersionResponse>;
  isCreating: boolean;
}

export function useCreatePromptVersion(): UseCreatePromptVersionReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ templateId, payload }: { templateId: string; payload: PromptVersionCreateRequest }) =>
      aiService.createPromptVersion(templateId, payload),
    onSuccess: (version) => {
      void queryClient.invalidateQueries({ queryKey: PROMPT_VERSIONS_QUERY_KEY(version.template_id) });
      void queryClient.invalidateQueries({ queryKey: PROMPT_TEMPLATES_QUERY_KEY });
      toast.success("Prompt version created.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createVersion: (args) => mutation.mutateAsync(args), isCreating: mutation.isPending };
}

export interface UseActivatePromptVersionReturn {
  activateVersion: (args: { templateId: string; versionId: string }) => Promise<PromptTemplateResponse>;
  isActivating: boolean;
}

export function useActivatePromptVersion(): UseActivatePromptVersionReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ templateId, versionId }: { templateId: string; versionId: string }) =>
      aiService.activatePromptVersion(templateId, versionId),
    onSuccess: (template) => {
      void queryClient.invalidateQueries({ queryKey: PROMPT_VERSIONS_QUERY_KEY(template.id) });
      void queryClient.invalidateQueries({ queryKey: PROMPT_TEMPLATES_QUERY_KEY });
      toast.success("Version activated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { activateVersion: (args) => mutation.mutateAsync(args), isActivating: mutation.isPending };
}
