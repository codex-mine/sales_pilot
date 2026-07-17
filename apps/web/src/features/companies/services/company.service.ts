import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  BulkActionResponse,
  BulkCompanyActionRequest,
  CompaniesQuery,
  CompanyActivityResponse,
  CompanyAttachmentResponse,
  CompanyCreateRequest,
  CompanyEmployeeResponse,
  CompanyNoteResponse,
  CompanyResponse,
  CompanyTagResponse,
  CompanyUpdateRequest,
  PaginationMeta,
} from "../types";

export async function getCompanies(
  query: CompaniesQuery = {},
  signal?: AbortSignal,
): Promise<{ companies: CompanyResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<CompanyResponse[]>>("/companies", { params: query, signal });
  return {
    companies: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getCompany(companyId: string, signal?: AbortSignal): Promise<CompanyResponse> {
  const { data } = await apiClient.get<ApiResponse<CompanyResponse>>(`/companies/${companyId}`, { signal });
  if (!data.data) throw new Error("Company not found.");
  return data.data;
}

export async function createCompany(payload: CompanyCreateRequest): Promise<CompanyResponse> {
  const { data } = await apiClient.post<ApiResponse<CompanyResponse>>("/companies", payload);
  if (!data.data) throw new Error("Company creation failed.");
  return data.data;
}

export async function updateCompany(companyId: string, payload: CompanyUpdateRequest): Promise<CompanyResponse> {
  const { data } = await apiClient.patch<ApiResponse<CompanyResponse>>(`/companies/${companyId}`, payload);
  if (!data.data) throw new Error("Company update failed.");
  return data.data;
}

export async function deleteCompany(companyId: string): Promise<void> {
  await apiClient.delete(`/companies/${companyId}`);
}

export async function archiveCompany(companyId: string): Promise<CompanyResponse> {
  const { data } = await apiClient.post<ApiResponse<CompanyResponse>>(`/companies/${companyId}/archive`);
  if (!data.data) throw new Error("Company archive failed.");
  return data.data;
}

export async function restoreCompany(companyId: string): Promise<CompanyResponse> {
  const { data } = await apiClient.post<ApiResponse<CompanyResponse>>(`/companies/${companyId}/restore`);
  if (!data.data) throw new Error("Company restore failed.");
  return data.data;
}

export async function uploadCompanyLogo(companyId: string, file: File): Promise<CompanyResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<ApiResponse<CompanyResponse>>(`/companies/${companyId}/logo`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  if (!data.data) throw new Error("Logo upload failed.");
  return data.data;
}

export async function deleteCompanyLogo(companyId: string): Promise<CompanyResponse> {
  const { data } = await apiClient.delete<ApiResponse<CompanyResponse>>(`/companies/${companyId}/logo`);
  if (!data.data) throw new Error("Logo removal failed.");
  return data.data;
}

export async function getCompanyTags(signal?: AbortSignal): Promise<CompanyTagResponse[]> {
  const { data } = await apiClient.get<ApiResponse<CompanyTagResponse[]>>("/companies/tags", { signal });
  return data.data ?? [];
}

export async function bulkCompanyAction(payload: BulkCompanyActionRequest): Promise<BulkActionResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkActionResponse>>("/companies/bulk", payload);
  if (!data.data) throw new Error("Bulk action failed.");
  return data.data;
}

export async function exportCompanies(
  query: CompaniesQuery & { company_ids?: string[] } = {},
): Promise<{ blob: Blob; filename: string }> {
  const response = await apiClient.get("/companies/export", { params: query, responseType: "blob" });
  return { blob: response.data as Blob, filename: "companies.csv" };
}

// ─── Employees (read-only Contact view) ─────────────────────────────────────────

export async function getCompanyEmployees(
  companyId: string,
  query: { search?: string; status?: string; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<{ employees: CompanyEmployeeResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<CompanyEmployeeResponse[]>>(`/companies/${companyId}/employees`, {
    params: query,
    signal,
  });
  return {
    employees: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

// ─── Notes ──────────────────────────────────────────────────────────────────────

export async function getCompanyNotes(companyId: string, signal?: AbortSignal): Promise<CompanyNoteResponse[]> {
  const { data } = await apiClient.get<ApiResponse<CompanyNoteResponse[]>>(`/companies/${companyId}/notes`, {
    signal,
  });
  return data.data ?? [];
}

export async function createCompanyNote(
  companyId: string,
  content: string,
  isPinned: boolean,
): Promise<CompanyNoteResponse> {
  const { data } = await apiClient.post<ApiResponse<CompanyNoteResponse>>(`/companies/${companyId}/notes`, {
    content,
    is_pinned: isPinned,
  });
  if (!data.data) throw new Error("Note creation failed.");
  return data.data;
}

export async function updateCompanyNote(
  companyId: string,
  noteId: string,
  payload: { content?: string; is_pinned?: boolean },
): Promise<CompanyNoteResponse> {
  const { data } = await apiClient.patch<ApiResponse<CompanyNoteResponse>>(
    `/companies/${companyId}/notes/${noteId}`,
    payload,
  );
  if (!data.data) throw new Error("Note update failed.");
  return data.data;
}

export async function deleteCompanyNote(companyId: string, noteId: string): Promise<void> {
  await apiClient.delete(`/companies/${companyId}/notes/${noteId}`);
}

// ─── Attachments ────────────────────────────────────────────────────────────────

export async function uploadCompanyAttachment(companyId: string, file: File): Promise<CompanyAttachmentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<ApiResponse<CompanyAttachmentResponse>>(
    `/companies/${companyId}/attachments`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  if (!data.data) throw new Error("Attachment upload failed.");
  return data.data;
}

export async function getCompanyAttachments(companyId: string): Promise<CompanyAttachmentResponse[]> {
  const { data } = await apiClient.get<ApiResponse<CompanyAttachmentResponse[]>>(
    `/companies/${companyId}/attachments`,
  );
  return data.data ?? [];
}

export async function deleteCompanyAttachment(companyId: string, attachmentId: string): Promise<void> {
  await apiClient.delete(`/companies/${companyId}/attachments/${attachmentId}`);
}

// ─── Activities ─────────────────────────────────────────────────────────────────

export async function getCompanyActivities(
  companyId: string,
  page = 1,
  pageSize = 50,
): Promise<{ activities: CompanyActivityResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<CompanyActivityResponse[]>>(
    `/companies/${companyId}/activities`,
    { params: { page, page_size: pageSize } },
  );
  return {
    activities: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: pageSize, total: 0 },
  };
}

export const companyService = {
  getCompanies,
  getCompany,
  createCompany,
  updateCompany,
  deleteCompany,
  archiveCompany,
  restoreCompany,
  uploadCompanyLogo,
  deleteCompanyLogo,
  getCompanyTags,
  bulkCompanyAction,
  exportCompanies,
  getCompanyEmployees,
  getCompanyNotes,
  createCompanyNote,
  updateCompanyNote,
  deleteCompanyNote,
  uploadCompanyAttachment,
  getCompanyAttachments,
  deleteCompanyAttachment,
  getCompanyActivities,
};
