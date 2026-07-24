import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  DuplicateEmailTemplateRequest,
  EmailTemplateCreateRequest,
  EmailTemplateResponse,
  EmailTemplatesQuery,
  EmailTemplateUpdateRequest,
  PaginationMeta,
} from "../types";

export async function getEmailTemplates(
  query: EmailTemplatesQuery = {},
  signal?: AbortSignal,
): Promise<{ templates: EmailTemplateResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<EmailTemplateResponse[]>>("/email-templates", {
    params: query,
    signal,
  });
  return {
    templates: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getEmailTemplate(templateId: string, signal?: AbortSignal): Promise<EmailTemplateResponse> {
  const { data } = await apiClient.get<ApiResponse<EmailTemplateResponse>>(`/email-templates/${templateId}`, {
    signal,
  });
  if (!data.data) throw new Error("Email template not found.");
  return data.data;
}

export async function createEmailTemplate(payload: EmailTemplateCreateRequest): Promise<EmailTemplateResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailTemplateResponse>>("/email-templates", payload);
  if (!data.data) throw new Error("Email template creation failed.");
  return data.data;
}

export async function duplicateEmailTemplate(
  templateId: string,
  payload: DuplicateEmailTemplateRequest = {},
): Promise<EmailTemplateResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailTemplateResponse>>(
    `/email-templates/${templateId}/duplicate`,
    payload,
  );
  if (!data.data) throw new Error("Email template duplication failed.");
  return data.data;
}

export async function updateEmailTemplate(
  templateId: string,
  payload: EmailTemplateUpdateRequest,
): Promise<EmailTemplateResponse> {
  const { data } = await apiClient.patch<ApiResponse<EmailTemplateResponse>>(
    `/email-templates/${templateId}`,
    payload,
  );
  if (!data.data) throw new Error("Email template update failed.");
  return data.data;
}

export async function deleteEmailTemplate(templateId: string): Promise<void> {
  await apiClient.delete(`/email-templates/${templateId}`);
}

export const emailTemplateService = {
  getEmailTemplates,
  getEmailTemplate,
  createEmailTemplate,
  duplicateEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
};
