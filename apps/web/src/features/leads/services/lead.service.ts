import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  ActivityResponse,
  AttachmentResponse,
  BulkActionResponse,
  BulkLeadActionRequest,
  ImportPreviewResponse,
  ImportResultResponse,
  LeadCreateRequest,
  LeadResponse,
  LeadsQuery,
  LeadUpdateRequest,
  NoteResponse,
  PaginationMeta,
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
};
