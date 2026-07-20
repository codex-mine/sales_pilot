// Mirrors the backend's app/schemas/analytics.py exactly (snake_case, same field names).

export const REPORT_TYPE_CHOICES = ["pipeline", "campaign_performance", "ai_usage", "email_performance"] as const;
export type ReportType = (typeof REPORT_TYPE_CHOICES)[number];

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  pipeline: "Pipeline funnel",
  campaign_performance: "Campaign performance",
  ai_usage: "AI usage & cost",
  email_performance: "Email performance",
};

// V1 scope: no cron-expression parser dependency — schedule_cron stores one
// of these cadence presets, not real cron syntax.
export const SCHEDULE_CADENCE_CHOICES = ["daily", "weekly", "monthly"] as const;
export type ScheduleCadence = (typeof SCHEDULE_CADENCE_CHOICES)[number];

export const DATE_RANGE_PRESETS = ["today", "last_7_days", "last_30_days", "this_month", "last_month", "all_time"] as const;
export type DateRangePreset = (typeof DATE_RANGE_PRESETS)[number];

export const DATE_RANGE_LABELS: Record<DateRangePreset, string> = {
  today: "Today",
  last_7_days: "Last 7 days",
  last_30_days: "Last 30 days",
  this_month: "This month",
  last_month: "Last month",
  all_time: "All time",
};

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

// ─── Dashboard summary ───────────────────────────────────────────────────────────

export interface PipelineFunnelResponse {
  counts: Record<string, number>;
}

export interface AIUsageJobTypeBreakdown {
  job_type: string;
  job_count: number;
  total_tokens: number;
  cost_usd: number;
}

export interface AIDailyCostPoint {
  date: string;
  cost_usd: number;
}

export interface AIUsageAnalyticsResponse {
  total_cost_usd: number;
  total_job_count: number;
  total_tokens: number;
  by_job_type: AIUsageJobTypeBreakdown[];
  daily_cost_trend: AIDailyCostPoint[];
}

export interface CampaignPerformanceItem {
  campaign_id: string;
  campaign_name: string;
  status: string;
  enrolled_count: number;
  replied_count: number;
  meeting_booked_count: number;
  reply_rate: number;
}

export interface CampaignPerformanceResponse {
  campaigns: CampaignPerformanceItem[];
}

export interface EmailPerformanceSummary {
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
}

export interface UpcomingMeetingItem {
  id: string;
  title: string;
  lead_full_name: string | null;
  scheduled_start: string | null;
}

export interface MeetingsSummary {
  by_status: Record<string, number>;
  booked_this_month: number;
  upcoming: UpcomingMeetingItem[];
}

export interface RecentActivityItem {
  id: string;
  activity_type: string;
  summary: string | null;
  actor_name: string | null;
  occurred_at: string;
}

export interface DashboardSummaryResponse {
  pipeline_funnel: PipelineFunnelResponse;
  ai_usage: AIUsageAnalyticsResponse;
  campaign_performance: CampaignPerformanceResponse;
  email_performance: EmailPerformanceSummary;
  meetings: MeetingsSummary;
  recent_activity: RecentActivityItem[];
  unread_notification_count: number;
}

// ─── Dashboard widgets ───────────────────────────────────────────────────────────

export interface DashboardWidgetResponse {
  id: string;
  widget_type: string;
  title: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  config: Record<string, unknown> | null;
}

export interface CreateDashboardWidgetRequest {
  widget_type: string;
  title: string;
  position_x?: number;
  position_y?: number;
  width?: number;
  height?: number;
  config?: Record<string, unknown>;
}

export type UpdateDashboardWidgetRequest = Partial<Omit<CreateDashboardWidgetRequest, "widget_type">>;

// ─── Reports ─────────────────────────────────────────────────────────────────────

export interface ReportConfig {
  filters?: Record<string, unknown>;
  columns?: string[];
  date_range?: DateRangePreset;
  group_by?: string | null;
}

export interface ReportResponse {
  id: string;
  organization_id: string;
  name: string;
  report_type: string;
  config: ReportConfig | null;
  is_scheduled: boolean;
  schedule_cron: string | null;
  recipients: string[] | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateReportRequest {
  name: string;
  report_type: ReportType;
  config?: ReportConfig;
  is_scheduled?: boolean;
  schedule_cron?: ScheduleCadence;
  recipients?: string[];
}

export type UpdateReportRequest = Partial<CreateReportRequest>;

export interface RunReportResponse {
  report: ReportResponse;
  row_count: number;
  delivered_to: string[];
}
