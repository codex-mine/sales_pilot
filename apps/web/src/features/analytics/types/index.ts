// Mirrors the backend's app/schemas/email_tracking.py exactly (snake_case,
// same field names).

export interface EmailPerformanceDailyPoint {
  date: string;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
}

export interface EmailPerformanceAnalyticsResponse {
  window_days: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_complained: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  daily: EmailPerformanceDailyPoint[];
}

export interface EmailPerformanceFilters {
  days?: number;
}
