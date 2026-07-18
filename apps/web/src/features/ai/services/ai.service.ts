import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  AIAgentCreateRequest,
  AIAgentResponse,
  AIAgentUpdateRequest,
  AIJobListItemResponse,
  AIJobResponse,
  AIJobsQuery,
  AIOutputResponse,
  AISettingsResponse,
  AISettingsUpdateRequest,
  AIUsageResponse,
  PaginationMeta,
  PromptTemplateCreateRequest,
  PromptTemplateResponse,
  PromptTemplateUpdateRequest,
  PromptVersionCreateRequest,
  PromptVersionResponse,
} from "../types";

// ─── Agents ──────────────────────────────────────────────────────────────────

export async function getAIAgents(signal?: AbortSignal): Promise<AIAgentResponse[]> {
  const { data } = await apiClient.get<ApiResponse<AIAgentResponse[]>>("/ai/agents", { signal });
  return data.data ?? [];
}

export async function getAIAgent(agentId: string, signal?: AbortSignal): Promise<AIAgentResponse> {
  const { data } = await apiClient.get<ApiResponse<AIAgentResponse>>(`/ai/agents/${agentId}`, { signal });
  if (!data.data) throw new Error("AI agent not found.");
  return data.data;
}

export async function createAIAgent(payload: AIAgentCreateRequest): Promise<AIAgentResponse> {
  const { data } = await apiClient.post<ApiResponse<AIAgentResponse>>("/ai/agents", payload);
  if (!data.data) throw new Error("AI agent creation failed.");
  return data.data;
}

export async function updateAIAgent(agentId: string, payload: AIAgentUpdateRequest): Promise<AIAgentResponse> {
  const { data } = await apiClient.patch<ApiResponse<AIAgentResponse>>(`/ai/agents/${agentId}`, payload);
  if (!data.data) throw new Error("AI agent update failed.");
  return data.data;
}

export async function deleteAIAgent(agentId: string): Promise<void> {
  await apiClient.delete(`/ai/agents/${agentId}`);
}

// ─── Jobs ────────────────────────────────────────────────────────────────────

export async function getAIJobs(
  query: AIJobsQuery = {},
  signal?: AbortSignal,
): Promise<{ jobs: AIJobListItemResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<AIJobListItemResponse[]>>("/ai/jobs", { params: query, signal });
  return {
    jobs: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getAIJob(jobId: string, signal?: AbortSignal): Promise<AIJobResponse> {
  const { data } = await apiClient.get<ApiResponse<AIJobResponse>>(`/ai/jobs/${jobId}`, { signal });
  if (!data.data) throw new Error("AI job not found.");
  return data.data;
}

export async function retryAIJob(jobId: string): Promise<AIJobResponse> {
  const { data } = await apiClient.post<ApiResponse<AIJobResponse>>(`/ai/jobs/${jobId}/retry`);
  if (!data.data) throw new Error("Retry failed.");
  return data.data;
}

export async function cancelAIJob(jobId: string): Promise<AIJobResponse> {
  const { data } = await apiClient.post<ApiResponse<AIJobResponse>>(`/ai/jobs/${jobId}/cancel`);
  if (!data.data) throw new Error("Cancel failed.");
  return data.data;
}

// ─── Outputs ─────────────────────────────────────────────────────────────────

export async function approveAIOutput(outputId: string): Promise<AIOutputResponse> {
  const { data } = await apiClient.post<ApiResponse<AIOutputResponse>>(`/ai/outputs/${outputId}/approve`);
  if (!data.data) throw new Error("Approval failed.");
  return data.data;
}

export async function rejectAIOutput(outputId: string): Promise<AIOutputResponse> {
  const { data } = await apiClient.post<ApiResponse<AIOutputResponse>>(`/ai/outputs/${outputId}/reject`);
  if (!data.data) throw new Error("Rejection failed.");
  return data.data;
}

// ─── Prompt templates / versions ────────────────────────────────────────────

export async function getPromptTemplates(signal?: AbortSignal): Promise<PromptTemplateResponse[]> {
  const { data } = await apiClient.get<ApiResponse<PromptTemplateResponse[]>>("/ai/prompt-templates", { signal });
  return data.data ?? [];
}

export async function getPromptTemplate(templateId: string, signal?: AbortSignal): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.get<ApiResponse<PromptTemplateResponse>>(`/ai/prompt-templates/${templateId}`, {
    signal,
  });
  if (!data.data) throw new Error("Prompt template not found.");
  return data.data;
}

export async function createPromptTemplate(payload: PromptTemplateCreateRequest): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.post<ApiResponse<PromptTemplateResponse>>("/ai/prompt-templates", payload);
  if (!data.data) throw new Error("Prompt template creation failed.");
  return data.data;
}

export async function updatePromptTemplate(
  templateId: string,
  payload: PromptTemplateUpdateRequest,
): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.patch<ApiResponse<PromptTemplateResponse>>(
    `/ai/prompt-templates/${templateId}`,
    payload,
  );
  if (!data.data) throw new Error("Prompt template update failed.");
  return data.data;
}

export async function getPromptVersions(templateId: string, signal?: AbortSignal): Promise<PromptVersionResponse[]> {
  const { data } = await apiClient.get<ApiResponse<PromptVersionResponse[]>>(
    `/ai/prompt-templates/${templateId}/versions`,
    { signal },
  );
  return data.data ?? [];
}

export async function createPromptVersion(
  templateId: string,
  payload: PromptVersionCreateRequest,
): Promise<PromptVersionResponse> {
  const { data } = await apiClient.post<ApiResponse<PromptVersionResponse>>(
    `/ai/prompt-templates/${templateId}/versions`,
    payload,
  );
  if (!data.data) throw new Error("Prompt version creation failed.");
  return data.data;
}

export async function activatePromptVersion(
  templateId: string,
  versionId: string,
): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.post<ApiResponse<PromptTemplateResponse>>(
    `/ai/prompt-templates/${templateId}/versions/${versionId}/activate`,
  );
  if (!data.data) throw new Error("Version activation failed.");
  return data.data;
}

// ─── Usage / settings ────────────────────────────────────────────────────────

export async function getAIUsage(days = 30, signal?: AbortSignal): Promise<AIUsageResponse> {
  const { data } = await apiClient.get<ApiResponse<AIUsageResponse>>("/ai/usage", { params: { days }, signal });
  if (!data.data) throw new Error("Usage fetch failed.");
  return data.data;
}

export async function getAISettings(signal?: AbortSignal): Promise<AISettingsResponse> {
  const { data } = await apiClient.get<ApiResponse<AISettingsResponse>>("/ai/settings", { signal });
  if (!data.data) throw new Error("Settings fetch failed.");
  return data.data;
}

export async function updateAISettings(payload: AISettingsUpdateRequest): Promise<AISettingsResponse> {
  const { data } = await apiClient.patch<ApiResponse<AISettingsResponse>>("/ai/settings", payload);
  if (!data.data) throw new Error("Settings update failed.");
  return data.data;
}

export const aiService = {
  getAIAgents,
  getAIAgent,
  createAIAgent,
  updateAIAgent,
  deleteAIAgent,
  getAIJobs,
  getAIJob,
  retryAIJob,
  cancelAIJob,
  approveAIOutput,
  rejectAIOutput,
  getPromptTemplates,
  getPromptTemplate,
  createPromptTemplate,
  updatePromptTemplate,
  getPromptVersions,
  createPromptVersion,
  activatePromptVersion,
  getAIUsage,
  getAISettings,
  updateAISettings,
};
