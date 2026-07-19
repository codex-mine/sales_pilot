import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  BulkEnrollRequest,
  BulkEnrollResponse,
  CampaignDashboardResponse,
  CampaignLeadResponse,
  CampaignLeadsQuery,
  CampaignResponse,
  CampaignsQuery,
  CreateCampaignRequest,
  CreateSequenceRequest,
  CreateSequenceStepRequest,
  EnrollByFilterRequest,
  EnrollLeadRequest,
  PaginationMeta,
  SequenceResponse,
  SequenceStepResponse,
  UpdateCampaignRequest,
  UpdateSequenceRequest,
  UpdateSequenceStepRequest,
} from "../types";

export async function getCampaigns(
  query: CampaignsQuery = {},
  signal?: AbortSignal,
): Promise<{ campaigns: CampaignResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<CampaignResponse[]>>("/campaigns", { params: query, signal });
  return {
    campaigns: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getCampaign(campaignId: string, signal?: AbortSignal): Promise<CampaignResponse> {
  const { data } = await apiClient.get<ApiResponse<CampaignResponse>>(`/campaigns/${campaignId}`, { signal });
  if (!data.data) throw new Error("Campaign not found.");
  return data.data;
}

export async function createCampaign(payload: CreateCampaignRequest): Promise<CampaignResponse> {
  const { data } = await apiClient.post<ApiResponse<CampaignResponse>>("/campaigns", payload);
  if (!data.data) throw new Error("Campaign creation failed.");
  return data.data;
}

export async function updateCampaign(campaignId: string, payload: UpdateCampaignRequest): Promise<CampaignResponse> {
  const { data } = await apiClient.patch<ApiResponse<CampaignResponse>>(`/campaigns/${campaignId}`, payload);
  if (!data.data) throw new Error("Campaign update failed.");
  return data.data;
}

export async function deleteCampaign(campaignId: string): Promise<void> {
  await apiClient.delete(`/campaigns/${campaignId}`);
}

export async function activateCampaign(campaignId: string): Promise<CampaignResponse> {
  const { data } = await apiClient.post<ApiResponse<CampaignResponse>>(`/campaigns/${campaignId}/activate`);
  if (!data.data) throw new Error("Campaign activation failed.");
  return data.data;
}

export async function pauseCampaign(campaignId: string): Promise<CampaignResponse> {
  const { data } = await apiClient.post<ApiResponse<CampaignResponse>>(`/campaigns/${campaignId}/pause`);
  if (!data.data) throw new Error("Campaign pause failed.");
  return data.data;
}

export async function archiveCampaign(campaignId: string): Promise<CampaignResponse> {
  const { data } = await apiClient.post<ApiResponse<CampaignResponse>>(`/campaigns/${campaignId}/archive`);
  if (!data.data) throw new Error("Campaign archive failed.");
  return data.data;
}

// ─── Sequences ──────────────────────────────────────────────────────────────────

export async function getCampaignSequences(campaignId: string, signal?: AbortSignal): Promise<SequenceResponse[]> {
  const { data } = await apiClient.get<ApiResponse<SequenceResponse[]>>(`/campaigns/${campaignId}/sequences`, {
    signal,
  });
  return data.data ?? [];
}

export async function createCampaignSequence(
  campaignId: string,
  payload: CreateSequenceRequest,
): Promise<SequenceResponse> {
  const { data } = await apiClient.post<ApiResponse<SequenceResponse>>(
    `/campaigns/${campaignId}/sequences`,
    payload,
  );
  if (!data.data) throw new Error("Sequence creation failed.");
  return data.data;
}

export async function updateSequence(sequenceId: string, payload: UpdateSequenceRequest): Promise<SequenceResponse> {
  const { data } = await apiClient.patch<ApiResponse<SequenceResponse>>(`/sequences/${sequenceId}`, payload);
  if (!data.data) throw new Error("Sequence update failed.");
  return data.data;
}

export async function createSequenceStep(
  sequenceId: string,
  payload: CreateSequenceStepRequest,
): Promise<SequenceStepResponse> {
  const { data } = await apiClient.post<ApiResponse<SequenceStepResponse>>(
    `/sequences/${sequenceId}/steps`,
    payload,
  );
  if (!data.data) throw new Error("Step creation failed.");
  return data.data;
}

export async function updateSequenceStep(
  stepId: string,
  payload: UpdateSequenceStepRequest,
): Promise<SequenceStepResponse> {
  const { data } = await apiClient.patch<ApiResponse<SequenceStepResponse>>(`/sequence-steps/${stepId}`, payload);
  if (!data.data) throw new Error("Step update failed.");
  return data.data;
}

export async function deleteSequenceStep(stepId: string): Promise<void> {
  await apiClient.delete(`/sequence-steps/${stepId}`);
}

export async function moveSequenceStep(stepId: string, direction: "up" | "down"): Promise<SequenceStepResponse[]> {
  const { data } = await apiClient.post<ApiResponse<SequenceStepResponse[]>>(
    `/sequence-steps/${stepId}/move`,
    null,
    { params: { direction } },
  );
  return data.data ?? [];
}

// ─── Enrollment ──────────────────────────────────────────────────────────────────

export async function enrollLead(campaignId: string, payload: EnrollLeadRequest): Promise<CampaignLeadResponse> {
  const { data } = await apiClient.post<ApiResponse<CampaignLeadResponse>>(
    `/campaigns/${campaignId}/enroll`,
    payload,
  );
  if (!data.data) throw new Error("Enrollment failed.");
  return data.data;
}

export async function enrollBulk(campaignId: string, payload: BulkEnrollRequest): Promise<BulkEnrollResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkEnrollResponse>>(
    `/campaigns/${campaignId}/enroll/bulk`,
    payload,
  );
  if (!data.data) throw new Error("Bulk enrollment failed.");
  return data.data;
}

export async function enrollByFilter(
  campaignId: string,
  payload: EnrollByFilterRequest,
): Promise<BulkEnrollResponse> {
  const { data } = await apiClient.post<ApiResponse<BulkEnrollResponse>>(
    `/campaigns/${campaignId}/enroll/by-filter`,
    payload,
  );
  if (!data.data) throw new Error("Enrollment by filter failed.");
  return data.data;
}

export async function unenrollCampaignLead(campaignLeadId: string, reason?: string): Promise<CampaignLeadResponse> {
  const { data } = await apiClient.delete<ApiResponse<CampaignLeadResponse>>(
    `/campaign-leads/${campaignLeadId}`,
    { params: reason ? { reason } : undefined },
  );
  if (!data.data) throw new Error("Unenroll failed.");
  return data.data;
}

export async function getCampaignLeads(
  campaignId: string,
  query: CampaignLeadsQuery = {},
  signal?: AbortSignal,
): Promise<{ campaignLeads: CampaignLeadResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<CampaignLeadResponse[]>>(`/campaigns/${campaignId}/leads`, {
    params: query,
    signal,
  });
  return {
    campaignLeads: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getLeadCampaigns(leadId: string, signal?: AbortSignal): Promise<CampaignLeadResponse[]> {
  const { data } = await apiClient.get<ApiResponse<CampaignLeadResponse[]>>(`/leads/${leadId}/campaigns`, { signal });
  return data.data ?? [];
}

// ─── Dashboard ───────────────────────────────────────────────────────────────────

export async function getCampaignDashboard(
  campaignId: string,
  signal?: AbortSignal,
): Promise<CampaignDashboardResponse> {
  const { data } = await apiClient.get<ApiResponse<CampaignDashboardResponse>>(
    `/campaigns/${campaignId}/dashboard`,
    { signal },
  );
  if (!data.data) throw new Error("Dashboard load failed.");
  return data.data;
}

export const campaignService = {
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  activateCampaign,
  pauseCampaign,
  archiveCampaign,
  getCampaignSequences,
  createCampaignSequence,
  updateSequence,
  createSequenceStep,
  updateSequenceStep,
  deleteSequenceStep,
  moveSequenceStep,
  enrollLead,
  enrollBulk,
  enrollByFilter,
  unenrollCampaignLead,
  getCampaignLeads,
  getLeadCampaigns,
  getCampaignDashboard,
};
