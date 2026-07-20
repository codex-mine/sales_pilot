// Mirrors the backend's app/schemas/campaigns.py exactly (snake_case, same field names).

export const CAMPAIGN_STATUS_CHOICES = ["draft", "active", "paused", "completed", "archived"] as const;
export type CampaignStatus = (typeof CAMPAIGN_STATUS_CHOICES)[number];

export const CAMPAIGN_STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: "Draft",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  archived: "Archived",
};

export const CAMPAIGN_LEAD_STATUS_CHOICES = [
  "enrolled", "in_progress", "replied", "meeting_booked", "completed", "opted_out", "bounced", "paused",
] as const;
export type CampaignLeadStatus = (typeof CAMPAIGN_LEAD_STATUS_CHOICES)[number];

export const CAMPAIGN_LEAD_STATUS_LABELS: Record<CampaignLeadStatus, string> = {
  enrolled: "Enrolled",
  in_progress: "In progress",
  replied: "Replied",
  meeting_booked: "Meeting booked",
  completed: "Completed",
  opted_out: "Opted out",
  bounced: "Bounced",
  paused: "Paused",
};

// V1 scope: linkedin_message / linkedin_connection / webhook exist on the
// backend enum for future extensibility but are rejected at creation time.
export const SUPPORTED_STEP_TYPES = ["email", "wait", "task"] as const;
export type StepType = (typeof SUPPORTED_STEP_TYPES)[number];

export const STEP_TYPE_LABELS: Record<StepType, string> = {
  email: "Email",
  wait: "Wait",
  task: "Task",
};

export const CONTENT_SOURCE_CHOICES = ["template", "ai_personalized"] as const;
export type ContentSource = (typeof CONTENT_SOURCE_CHOICES)[number];

export const SEND_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const;
export type SendDay = (typeof SEND_DAYS)[number];

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

// ─── Campaign ────────────────────────────────────────────────────────────────────

export interface CampaignOwnerResponse {
  id: string;
  full_name: string;
  email: string;
}

export interface CampaignFunnelCounts {
  enrolled: number;
  in_progress: number;
  replied: number;
  meeting_booked: number;
  completed: number;
  opted_out: number;
  bounced: number;
}

export interface CampaignResponse {
  id: string;
  organization_id: string;
  owner: CampaignOwnerResponse | null;
  name: string;
  description: string | null;
  status: string;
  goal: string | null;
  target_industry: string | null;
  target_company_size: string | null;
  target_job_titles: string[] | null;
  value_proposition: string | null;
  daily_send_limit: number;
  timezone: string;
  send_days: string[];
  send_start_hour: number;
  send_end_hour: number;
  requires_approval: boolean;
  started_at: string | null;
  completed_at: string | null;
  enrolled_count: number;
  funnel: CampaignFunnelCounts | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCampaignRequest {
  name: string;
  description?: string;
  goal?: string;
  target_industry?: string;
  target_company_size?: string;
  target_job_titles?: string[];
  value_proposition?: string;
  daily_send_limit?: number;
  timezone?: string;
  send_days?: string[];
  send_start_hour?: number;
  send_end_hour?: number;
  owner_id?: string;
  requires_approval?: boolean;
}

export type UpdateCampaignRequest = Partial<CreateCampaignRequest>;

export interface CampaignsQuery {
  status?: string[];
  search?: string;
  page?: number;
  page_size?: number;
}

// ─── Sequence ────────────────────────────────────────────────────────────────────

export interface SequenceStepTemplateSummary {
  id: string;
  name: string;
  subject: string;
  total_sent: number;
  total_opened: number;
  total_replied: number;
  open_rate: number;
  reply_rate: number;
}

export interface SequenceStepCondition {
  skip_if?: string;
  only_if?: string;
}

export interface SequenceStepResponse {
  id: string;
  sequence_id: string;
  step_type: string;
  step_order: number;
  delay_days: number;
  delay_hours: number;
  email_template_id: string | null;
  email_template: SequenceStepTemplateSummary | null;
  content_source: string;
  subject_override: string | null;
  body_override: string | null;
  condition: SequenceStepCondition | null;
  is_active: boolean;
}

export interface SequenceResponse {
  id: string;
  campaign_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  steps: SequenceStepResponse[];
  created_at: string;
}

export interface CreateSequenceRequest {
  name: string;
  description?: string;
  is_active?: boolean;
}

export type UpdateSequenceRequest = Partial<CreateSequenceRequest>;

export interface CreateSequenceStepRequest {
  step_type: StepType;
  step_order: number;
  delay_days?: number;
  delay_hours?: number;
  email_template_id?: string;
  content_source?: ContentSource;
  subject_override?: string;
  body_override?: string;
  condition?: SequenceStepCondition;
  is_active?: boolean;
}

export type UpdateSequenceStepRequest = Partial<CreateSequenceStepRequest>;

// ─── Enrollment ──────────────────────────────────────────────────────────────────

export interface EnrollLeadRequest {
  lead_id: string;
  sequence_id?: string;
}

export interface BulkEnrollRequest {
  lead_ids: string[];
  sequence_id?: string;
}

export interface EnrollByFilterRequest {
  sequence_id?: string;
  search?: string;
  status?: string[];
  source?: string[];
  owner_id?: string[];
  tag?: string[];
  country?: string;
  industry?: string;
  company?: string;
  favorite?: boolean;
  archived?: boolean;
  lead_score_min?: number;
  lead_score_max?: number;
  priority_min?: number;
  priority_max?: number;
  created_from?: string;
  created_to?: string;
  updated_from?: string;
  updated_to?: string;
}

export interface BulkEnrollResponse {
  requested_count: number;
  enrolled_count: number;
  skipped_count: number;
  errors: string[];
}

export interface CampaignLeadLeadSummary {
  id: string;
  full_name: string;
  email: string | null;
  company_name: string | null;
  status: string;
}

export interface CampaignLeadResponse {
  id: string;
  campaign_id: string;
  campaign_name: string | null;
  lead: CampaignLeadLeadSummary | null;
  sequence_id: string | null;
  status: string;
  current_step_order: number;
  next_step_id: string | null;
  next_step_type: string | null;
  next_action_at: string | null;
  enrolled_at: string;
  completed_at: string | null;
  opted_out_at: string | null;
}

export interface CampaignLeadsQuery {
  status?: string[];
  page?: number;
  page_size?: number;
}

// ─── Dashboard ───────────────────────────────────────────────────────────────────

export interface CampaignDashboardResponse {
  campaign_id: string;
  status: string;
  funnel: CampaignFunnelCounts;
  total_enrolled: number;
  emails_sent: number;
  open_rate: number;
  reply_rate: number;
  meeting_rate: number;
}
