import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  AIUsageAnalyticsResponse,
  CampaignPerformanceResponse,
  CreateDashboardWidgetRequest,
  CreateReportRequest,
  DashboardSummaryResponse,
  DashboardWidgetResponse,
  PaginationMeta,
  PipelineFunnelResponse,
  ReportResponse,
  RunReportResponse,
  UpdateDashboardWidgetRequest,
  UpdateReportRequest,
} from "../types";

export async function getDashboardSummary(signal?: AbortSignal): Promise<DashboardSummaryResponse> {
  const { data } = await apiClient.get<ApiResponse<DashboardSummaryResponse>>("/dashboard/summary", { signal });
  if (!data.data) throw new Error("Failed to load dashboard.");
  return data.data;
}

export async function getDashboardWidgets(signal?: AbortSignal): Promise<DashboardWidgetResponse[]> {
  const { data } = await apiClient.get<ApiResponse<DashboardWidgetResponse[]>>("/dashboard/widgets", { signal });
  return data.data ?? [];
}

export async function createDashboardWidget(payload: CreateDashboardWidgetRequest): Promise<DashboardWidgetResponse> {
  const { data } = await apiClient.post<ApiResponse<DashboardWidgetResponse>>("/dashboard/widgets", payload);
  if (!data.data) throw new Error("Failed to add widget.");
  return data.data;
}

export async function updateDashboardWidget(
  widgetId: string,
  payload: UpdateDashboardWidgetRequest,
): Promise<DashboardWidgetResponse> {
  const { data } = await apiClient.patch<ApiResponse<DashboardWidgetResponse>>(`/dashboard/widgets/${widgetId}`, payload);
  if (!data.data) throw new Error("Failed to update widget.");
  return data.data;
}

export async function deleteDashboardWidget(widgetId: string): Promise<void> {
  await apiClient.delete(`/dashboard/widgets/${widgetId}`);
}

export async function getPipelineFunnel(signal?: AbortSignal): Promise<PipelineFunnelResponse> {
  const { data } = await apiClient.get<ApiResponse<PipelineFunnelResponse>>("/analytics/pipeline-funnel", { signal });
  if (!data.data) throw new Error("Failed to load pipeline funnel.");
  return data.data;
}

export async function getAIUsageAnalytics(signal?: AbortSignal): Promise<AIUsageAnalyticsResponse> {
  const { data } = await apiClient.get<ApiResponse<AIUsageAnalyticsResponse>>("/analytics/ai-usage", { signal });
  if (!data.data) throw new Error("Failed to load AI usage.");
  return data.data;
}

export async function getCampaignPerformanceAnalytics(
  limit = 10,
  signal?: AbortSignal,
): Promise<CampaignPerformanceResponse> {
  const { data } = await apiClient.get<ApiResponse<CampaignPerformanceResponse>>("/analytics/campaign-performance", {
    params: { limit },
    signal,
  });
  if (!data.data) throw new Error("Failed to load campaign performance.");
  return data.data;
}

// ─── Reports ─────────────────────────────────────────────────────────────────────

export async function getReports(
  query: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<{ reports: ReportResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<ReportResponse[]>>("/reports", { params: query, signal });
  return {
    reports: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getReport(reportId: string, signal?: AbortSignal): Promise<ReportResponse> {
  const { data } = await apiClient.get<ApiResponse<ReportResponse>>(`/reports/${reportId}`, { signal });
  if (!data.data) throw new Error("Report not found.");
  return data.data;
}

export async function createReport(payload: CreateReportRequest): Promise<ReportResponse> {
  const { data } = await apiClient.post<ApiResponse<ReportResponse>>("/reports", payload);
  if (!data.data) throw new Error("Failed to create report.");
  return data.data;
}

export async function updateReport(reportId: string, payload: UpdateReportRequest): Promise<ReportResponse> {
  const { data } = await apiClient.patch<ApiResponse<ReportResponse>>(`/reports/${reportId}`, payload);
  if (!data.data) throw new Error("Failed to update report.");
  return data.data;
}

export async function deleteReport(reportId: string): Promise<void> {
  await apiClient.delete(`/reports/${reportId}`);
}

export async function runReport(reportId: string): Promise<RunReportResponse> {
  const { data } = await apiClient.post<ApiResponse<RunReportResponse>>(`/reports/${reportId}/run`);
  if (!data.data) throw new Error("Failed to run report.");
  return data.data;
}

export const dashboardService = {
  getDashboardSummary,
  getDashboardWidgets,
  createDashboardWidget,
  updateDashboardWidget,
  deleteDashboardWidget,
  getPipelineFunnel,
  getAIUsageAnalytics,
  getCampaignPerformanceAnalytics,
  getReports,
  getReport,
  createReport,
  updateReport,
  deleteReport,
  runReport,
};
