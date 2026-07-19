import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type { EmailPerformanceAnalyticsResponse, EmailPerformanceFilters } from "../types";

export async function getEmailPerformanceAnalytics(
  filters: EmailPerformanceFilters = {},
  signal?: AbortSignal,
): Promise<EmailPerformanceAnalyticsResponse> {
  const { data } = await apiClient.get<ApiResponse<EmailPerformanceAnalyticsResponse>>(
    "/analytics/email-performance",
    { params: filters, signal },
  );
  if (!data.data) throw new Error("Email performance analytics not available.");
  return data.data;
}

export const analyticsService = {
  getEmailPerformanceAnalytics,
};
