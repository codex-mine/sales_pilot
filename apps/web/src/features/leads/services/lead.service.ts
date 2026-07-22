import type { AIJobResponse, AIOutputResponse } from "@/features/ai/types";
import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  ActivityResponse,
  ApproveEmailVariantRequest,
  AttachmentResponse,
  BulkActionResponse,
  BulkEmailGenerationResponse,
  BulkLeadActionRequest,
  BulkLeadEmailGenerationRequest,
  BulkLeadResearchRequest,
  BulkResearchResponse,
  BulkSendRequest,
  BulkSendResponse,
  ComposeEmailRequest,
  EmailEventResponse,
  EmailPreviewResponse,
  EmailResponse,
  EmailTimelineResponse,
  GenerateEmailRequest,
  ImportPreviewResponse,
  ImportResultResponse,
  LeadCreateRequest,
  LeadResearchStatusResponse,
  LeadResponse,
  LeadsQuery,
  LeadUpdateRequest,
  NoteResponse,
  OutboxEmailResponse,
  PaginationMeta,
  ProspectAnalysisResponse,
  RegenerateEmailRequest,
  ScheduleEmailRequest,
  TagResponse,
} from "../types";

export async function getLeads(
  query: LeadsQuery = {},
  signal?: AbortSignal,
): Promise<{ leads: LeadResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<LeadResponse[]>>("/leads", { params: query, signal });
  return {
    leads: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getLead(leadId: string, signal?: AbortSignal): Promise<LeadResponse> {
  const { data } = await apiClient.get<ApiResponse<LeadResponse>>(`/leads/${leadId}`, { signal });
  if (!data.data) throw new Error("Lead not found.");
  return data.data;
}

export async function createLead(payload: LeadCreateRequest): Promise<LeadResponse> {
  const { data } = await apiClient.post<ApiResponse<LeadResponse>>("/leads", payload);
  if (!data.data) throw new Error("Lead creation failed.");
  return data.data;
}

export async function updateLead(leadId: string, payload: LeadUpdateRequest): Promise<LeadResponse> {
  const { data } = await apiClient.patch<ApiResponse<LeadResponse>>(`/leads/${leadId}`, payload);
  if (!data.data) throw new Error("Lead update failed.");
  return data.data;
}

export async function deleteLead(leadId: string): Promise<void> {
  await apiClient.delete(`/leads/${leadId}`);
}

export async function getLeadTags(signal?: AbortSignal): Promise<TagResponse[]> {
  const { data } = await apiClient.get<ApiResponse<TagResponse[]>>("/leads/tags", { signal });
  return data.data ?? [];
}

export async function bulkLeadAction(payload: BulkLeadActionRequest): Promise<BulkActionResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkActionResponse>>("/leads/bulk", payload);
  if (!data.data) throw new Error("Bulk action failed.");
  return data.data;
}

export async function previewImport(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mode", "preview");
  const { data } = await apiClient.post<ApiResponse<ImportPreviewResponse>>("/leads/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  if (!data.data) throw new Error("Import preview failed.");
  return data.data;
}

export async function commitImport(file: File, mapping: Record<string, string>): Promise<ImportResultResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mode", "commit");
  formData.append("mapping", JSON.stringify(mapping));
  const { data } = await apiClient.post<ApiResponse<ImportResultResponse>>("/leads/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  if (!data.data) throw new Error("Import failed.");
  return data.data;
}

export async function exportLeads(
  query: LeadsQuery & { lead_ids?: string[] } = {},
): Promise<{ blob: Blob; filename: string }> {
  const response = await apiClient.get("/leads/export", { params: query, responseType: "blob" });
  return { blob: response.data as Blob, filename: "leads.csv" };
}

// ─── Notes ──────────────────────────────────────────────────────────────────────

export async function getNotes(leadId: string, signal?: AbortSignal): Promise<NoteResponse[]> {
  const { data } = await apiClient.get<ApiResponse<NoteResponse[]>>(`/leads/${leadId}/notes`, { signal });
  return data.data ?? [];
}

export async function createNote(leadId: string, content: string, isPinned: boolean): Promise<NoteResponse> {
  const { data } = await apiClient.post<ApiResponse<NoteResponse>>(`/leads/${leadId}/notes`, {
    content,
    is_pinned: isPinned,
  });
  if (!data.data) throw new Error("Note creation failed.");
  return data.data;
}

export async function updateNote(
  leadId: string,
  noteId: string,
  payload: { content?: string; is_pinned?: boolean },
): Promise<NoteResponse> {
  const { data } = await apiClient.patch<ApiResponse<NoteResponse>>(`/leads/${leadId}/notes/${noteId}`, payload);
  if (!data.data) throw new Error("Note update failed.");
  return data.data;
}

export async function deleteNote(leadId: string, noteId: string): Promise<void> {
  await apiClient.delete(`/leads/${leadId}/notes/${noteId}`);
}

// ─── Attachments ────────────────────────────────────────────────────────────────

export async function uploadAttachment(leadId: string, file: File): Promise<AttachmentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<ApiResponse<AttachmentResponse>>(
    `/leads/${leadId}/attachments`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  if (!data.data) throw new Error("Attachment upload failed.");
  return data.data;
}

export async function getAttachments(leadId: string): Promise<AttachmentResponse[]> {
  const { data } = await apiClient.get<ApiResponse<AttachmentResponse[]>>(`/leads/${leadId}/attachments`);
  return data.data ?? [];
}

export async function deleteAttachment(leadId: string, attachmentId: string): Promise<void> {
  await apiClient.delete(`/leads/${leadId}/attachments/${attachmentId}`);
}

// ─── Research (AI -> Prospect Analysis, combined "Research this Lead") ──────────

export async function triggerLeadResearch(leadId: string, force = false): Promise<LeadResearchStatusResponse> {
  const { data } = await apiClient.post<ApiResponse<LeadResearchStatusResponse>>(
    `/leads/${leadId}/research`,
    null,
    { params: force ? { force: true } : undefined },
  );
  if (!data.data) throw new Error("Research trigger failed.");
  return data.data;
}

export async function getLeadResearch(leadId: string, signal?: AbortSignal): Promise<LeadResearchStatusResponse> {
  const { data } = await apiClient.get<ApiResponse<LeadResearchStatusResponse>>(`/leads/${leadId}/research`, {
    signal,
  });
  if (!data.data) throw new Error("Lead research status not found.");
  return data.data;
}

export async function getProspectAnalysis(
  leadId: string,
  signal?: AbortSignal,
): Promise<ProspectAnalysisResponse | null> {
  const { data } = await apiClient.get<ApiResponse<ProspectAnalysisResponse | null>>(
    `/leads/${leadId}/prospect-analysis`,
    { signal },
  );
  return data.data ?? null;
}

export async function bulkTriggerResearch(payload: BulkLeadResearchRequest): Promise<BulkResearchResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkResearchResponse>>("/leads/bulk/research", payload);
  if (!data.data) throw new Error("Bulk research trigger failed.");
  return data.data;
}

// ─── Email Generation (AI -> Personalized Email + Human Review) ─────────────────

export async function generateLeadEmail(leadId: string, payload: GenerateEmailRequest): Promise<AIJobResponse> {
  const { data } = await apiClient.post<ApiResponse<AIJobResponse>>(`/leads/${leadId}/emails/generate`, payload);
  if (!data.data) throw new Error("Email generation failed.");
  return data.data;
}

export async function getLeadEmailDrafts(leadId: string, signal?: AbortSignal): Promise<EmailResponse[]> {
  const { data } = await apiClient.get<ApiResponse<EmailResponse[]>>(`/leads/${leadId}/emails/drafts`, { signal });
  return data.data ?? [];
}

export async function regenerateLeadEmail(leadId: string, payload: RegenerateEmailRequest): Promise<AIJobResponse> {
  const { data } = await apiClient.post<ApiResponse<AIJobResponse>>(`/leads/${leadId}/emails/regenerate`, payload);
  if (!data.data) throw new Error("Regeneration failed.");
  return data.data;
}

export async function bulkGenerateEmails(
  payload: BulkLeadEmailGenerationRequest,
): Promise<BulkEmailGenerationResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkEmailGenerationResponse>>(
    "/leads/bulk/generate-emails",
    payload,
  );
  if (!data.data) throw new Error("Bulk email generation failed.");
  return data.data;
}

export async function approveEmailVariant(
  outputId: string,
  payload: ApproveEmailVariantRequest,
): Promise<EmailResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailResponse>>(
    `/ai/outputs/${outputId}/approve-email`,
    payload,
  );
  if (!data.data) throw new Error("Approval failed.");
  return data.data;
}

export async function rejectEmailVariant(outputId: string): Promise<AIOutputResponse> {
  const { data } = await apiClient.post<ApiResponse<AIOutputResponse>>(`/ai/outputs/${outputId}/reject-email`);
  if (!data.data) throw new Error("Rejection failed.");
  return data.data;
}

// ─── Activities ─────────────────────────────────────────────────────────────────

export async function getActivities(
  leadId: string,
  page = 1,
  pageSize = 50,
): Promise<{ activities: ActivityResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<ActivityResponse[]>>(`/leads/${leadId}/activities`, {
    params: { page, page_size: pageSize },
  });
  return {
    activities: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: pageSize, total: 0 },
  };
}

// ─── Email Sending (Communication -> Send Draft Email) ──────────────────────────

export async function composeLeadEmail(leadId: string, payload: ComposeEmailRequest): Promise<EmailResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailResponse>>(`/leads/${leadId}/emails/compose`, payload);
  if (!data.data) throw new Error("Failed to send the email.");
  return data.data;
}

export async function sendLeadEmail(leadId: string, emailId: string): Promise<EmailResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailResponse>>(
    `/leads/${leadId}/emails/${emailId}/send`,
  );
  if (!data.data) throw new Error("Send failed.");
  return data.data;
}

export async function scheduleLeadEmail(
  leadId: string,
  emailId: string,
  payload: ScheduleEmailRequest,
): Promise<EmailResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailResponse>>(
    `/leads/${leadId}/emails/${emailId}/schedule`,
    payload,
  );
  if (!data.data) throw new Error("Schedule failed.");
  return data.data;
}

export async function cancelLeadEmail(leadId: string, emailId: string): Promise<EmailResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailResponse>>(
    `/leads/${leadId}/emails/${emailId}/cancel`,
  );
  if (!data.data) throw new Error("Cancel failed.");
  return data.data;
}

export async function getEmailPreview(emailId: string, signal?: AbortSignal): Promise<EmailPreviewResponse> {
  const { data } = await apiClient.get<ApiResponse<EmailPreviewResponse>>(`/emails/${emailId}/preview`, { signal });
  if (!data.data) throw new Error("Preview not available.");
  return data.data;
}

export async function getEmailEvents(emailId: string, signal?: AbortSignal): Promise<EmailEventResponse[]> {
  const { data } = await apiClient.get<ApiResponse<EmailEventResponse[]>>(`/emails/${emailId}/events`, { signal });
  return data.data ?? [];
}

export async function getEmailTimeline(emailId: string, signal?: AbortSignal): Promise<EmailTimelineResponse> {
  const { data } = await apiClient.get<ApiResponse<EmailTimelineResponse>>(`/emails/${emailId}/timeline`, { signal });
  if (!data.data) throw new Error("Timeline not available.");
  return data.data;
}

export async function getEmailOutbox(
  query: { status?: string[]; search?: string; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<{ emails: OutboxEmailResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<OutboxEmailResponse[]>>("/emails/outbox", {
    params: query,
    signal,
  });
  return {
    emails: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function bulkSendEmails(payload: BulkSendRequest): Promise<BulkSendResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkSendResponse>>("/emails/bulk-send", payload);
  if (!data.data) throw new Error("Bulk send failed.");
  return data.data;
}

export const leadService = {
  getLeads,
  getLead,
  createLead,
  updateLead,
  deleteLead,
  getLeadTags,
  bulkLeadAction,
  previewImport,
  commitImport,
  exportLeads,
  getNotes,
  createNote,
  updateNote,
  deleteNote,
  uploadAttachment,
  getAttachments,
  deleteAttachment,
  getActivities,
  triggerLeadResearch,
  getLeadResearch,
  getProspectAnalysis,
  bulkTriggerResearch,
  generateLeadEmail,
  getLeadEmailDrafts,
  regenerateLeadEmail,
  bulkGenerateEmails,
  approveEmailVariant,
  rejectEmailVariant,
  composeLeadEmail,
  sendLeadEmail,
  scheduleLeadEmail,
  cancelLeadEmail,
  getEmailPreview,
  getEmailEvents,
  getEmailTimeline,
  getEmailOutbox,
  bulkSendEmails,
};
