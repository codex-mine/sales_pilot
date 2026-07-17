// Mirrors the backend's app/schemas/leads.py exactly (snake_case, same field names).

export const LEAD_STATUS_CHOICES = [
  "new", "contacted", "qualified", "interested", "demo_scheduled",
  "proposal", "negotiation", "won", "lost",
] as const;
export type LeadStatus = (typeof LEAD_STATUS_CHOICES)[number];

export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  new: "New",
  contacted: "Contacted",
  qualified: "Qualified",
  interested: "Interested",
  demo_scheduled: "Meeting Scheduled",
  proposal: "Proposal Sent",
  negotiation: "Negotiation",
  won: "Won",
  lost: "Lost",
};

export const LEAD_SOURCE_CHOICES = [
  "website", "manual", "csv_import", "referral", "linkedin", "apollo",
  "google_maps", "facebook", "cold_email", "advertisement", "api", "custom",
] as const;
export type LeadSource = (typeof LEAD_SOURCE_CHOICES)[number];

export const LEAD_SOURCE_LABELS: Record<LeadSource, string> = {
  website: "Website",
  manual: "Manual",
  csv_import: "CSV Import",
  referral: "Referral",
  linkedin: "LinkedIn",
  apollo: "Apollo",
  google_maps: "Google Maps",
  facebook: "Facebook",
  cold_email: "Cold Email",
  advertisement: "Advertisement",
  api: "API",
  custom: "Custom",
};

export const COMPANY_SIZE_CHOICES = ["1", "2-10", "11-50", "51-200", "201-1000", "1001-5000", "5000+"] as const;
export type LeadCompanySize = (typeof COMPANY_SIZE_CHOICES)[number];

export interface LeadAddress {
  line1?: string | null;
  line2?: string | null;
  postal_code?: string | null;
}

export interface TagResponse {
  id: string;
  name: string;
  color: string | null;
}

export interface LeadOwnerResponse {
  id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
}

export interface LeadResponse {
  id: string;
  organization_id: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  company_name: string | null;
  website: string | null;
  industry: string | null;
  source: string | null;
  status: string;
  priority: number;
  country: string | null;
  state: string | null;
  city: string | null;
  address: LeadAddress | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  company_size: string | null;
  revenue: number | null;
  employee_count: number | null;
  owner: LeadOwnerResponse | null;
  tags: TagResponse[];
  description: string | null;
  lead_score: number | null;
  notes_count: number;
  attachments_count: number;
  activities_count: number;
  is_favorite: boolean;
  is_archived: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadCreateRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  job_title?: string;
  company_name?: string;
  website?: string;
  industry?: string;
  source?: string;
  status?: string;
  priority?: number;
  country?: string;
  state?: string;
  city?: string;
  address?: LeadAddress;
  linkedin_url?: string;
  twitter_url?: string;
  company_size?: string;
  revenue?: number;
  employee_count?: number;
  owner_id?: string;
  tags?: string[];
  description?: string;
  lead_score?: number;
}

export interface LeadUpdateRequest extends Partial<LeadCreateRequest> {
  is_favorite?: boolean;
  is_archived?: boolean;
}

export interface LeadsQuery {
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
  sort_by?: "name" | "company" | "lead_score" | "status" | "created_at" | "updated_at" | "priority";
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface NoteResponse {
  id: string;
  lead_id: string;
  author_id: string | null;
  author_name: string | null;
  content: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface AttachmentResponse {
  id: string;
  lead_id: string;
  filename: string;
  file_url: string;
  file_size: number | null;
  mime_type: string | null;
  uploaded_by: string | null;
  uploaded_by_name: string | null;
  created_at: string;
}

export interface ActivityResponse {
  id: string;
  lead_id: string;
  actor_id: string | null;
  actor_name: string | null;
  activity_type: string;
  summary: string | null;
  metadata: Record<string, unknown> | null;
  occurred_at: string;
}

export type BulkActionType =
  | "delete" | "archive" | "restore" | "favorite" | "unfavorite"
  | "assign_owner" | "change_status" | "add_tags" | "remove_tags";

export interface BulkLeadActionRequest {
  lead_ids: string[];
  action: BulkActionType;
  owner_id?: string;
  status?: string;
  tags?: string[];
}

export interface BulkActionError {
  lead_id: string;
  message: string;
}

export interface BulkActionResponse {
  action: string;
  requested_count: number;
  success_count: number;
  failed_count: number;
  errors: BulkActionError[];
}

export interface ImportPreviewResponse {
  headers: string[];
  sample_rows: Record<string, string>[];
  suggested_mapping: Record<string, string>;
  total_rows: number;
  available_fields: string[];
}

export interface ImportFailedRow {
  row_number: number;
  errors: string[];
  data: Record<string, string>;
}

export interface ImportResultResponse {
  total_rows: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  failed_rows: ImportFailedRow[];
}
