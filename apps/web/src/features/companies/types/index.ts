// Mirrors the backend's app/schemas/companies.py exactly (snake_case, same field names).

export const COMPANY_STATUS_CHOICES = ["prospect", "active", "customer", "partner", "churned", "inactive"] as const;
export type CompanyStatus = (typeof COMPANY_STATUS_CHOICES)[number];

export const COMPANY_STATUS_LABELS: Record<CompanyStatus, string> = {
  prospect: "Prospect",
  active: "Active",
  customer: "Customer",
  partner: "Partner",
  churned: "Churned",
  inactive: "Inactive",
};

export const COMPANY_SIZE_CHOICES = ["1", "2-10", "11-50", "51-200", "201-1000", "1001-5000", "5000+"] as const;
export type CompanySize = (typeof COMPANY_SIZE_CHOICES)[number];

export interface CompanyAddress {
  line1?: string | null;
  line2?: string | null;
}

export interface CompanyTagResponse {
  id: string;
  name: string;
  color: string | null;
}

export interface CompanyOwnerResponse {
  id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
}

export interface CompanyResponse {
  id: string;
  organization_id: string;
  name: string;
  legal_name: string | null;
  logo_url: string | null;
  website: string | null;
  domain: string | null;
  industry: string | null;
  description: string | null;
  phone: string | null;
  email: string | null;
  founded_year: number | null;
  size_range: string | null;
  employee_count: number | null;
  annual_revenue: number | null;
  currency: string;
  country: string | null;
  state: string | null;
  city: string | null;
  postal_code: string | null;
  address: CompanyAddress | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  status: string;
  owner: CompanyOwnerResponse | null;
  tags: CompanyTagResponse[];
  contact_count: number;
  lead_count: number;
  notes_count: number;
  attachments_count: number;
  is_archived: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyCreateRequest {
  name: string;
  legal_name?: string;
  website?: string;
  industry?: string;
  description?: string;
  phone?: string;
  email?: string;
  founded_year?: number;
  size_range?: string;
  annual_revenue?: number;
  currency?: string;
  country?: string;
  state?: string;
  city?: string;
  postal_code?: string;
  address?: CompanyAddress;
  linkedin_url?: string;
  twitter_url?: string;
  facebook_url?: string;
  instagram_url?: string;
  status?: string;
  owner_id?: string;
  tags?: string[];
}

export type CompanyUpdateRequest = Partial<CompanyCreateRequest>;

export interface CompaniesQuery {
  search?: string;
  status?: string[];
  industry?: string[];
  size_range?: string[];
  owner_id?: string[];
  tag?: string[];
  country?: string;
  archived?: boolean;
  revenue_min?: number;
  revenue_max?: number;
  employee_count_min?: number;
  employee_count_max?: number;
  created_from?: string;
  created_to?: string;
  updated_from?: string;
  updated_to?: string;
  sort_by?: "name" | "industry" | "status" | "employee_count" | "annual_revenue" | "created_at" | "updated_at";
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface CompanyNoteResponse {
  id: string;
  company_id: string;
  author_id: string | null;
  author_name: string | null;
  content: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface CompanyAttachmentResponse {
  id: string;
  company_id: string;
  filename: string;
  file_url: string;
  file_size: number | null;
  mime_type: string | null;
  uploaded_by: string | null;
  uploaded_by_name: string | null;
  created_at: string;
}

export interface CompanyActivityResponse {
  id: string;
  company_id: string;
  actor_id: string | null;
  actor_name: string | null;
  activity_type: string;
  summary: string | null;
  metadata: Record<string, unknown> | null;
  occurred_at: string;
}

export interface CompanyEmployeeResponse {
  id: string;
  full_name: string;
  job_title: string | null;
  department: string | null;
  email: string;
  phone: string | null;
  status: string;
  is_decision_maker: boolean | null;
  has_linked_lead: boolean;
  last_activity_at: string;
  created_at: string;
}

// ─── Research (AI -> Company Research) ──────────────────────────────────────────

export const DATA_QUALITY_CHOICES = ["web_enriched", "llm_knowledge_only"] as const;
export type DataQuality = (typeof DATA_QUALITY_CHOICES)[number];

export interface CompanyResearchResponse {
  id: string;
  company_id: string;
  ai_job_id: string | null;
  summary: string | null;
  products_services: string[] | null;
  target_customers: string | null;
  business_model: string | null;
  technologies: string[] | null;
  competitors: string[] | null;
  recent_news: string[] | null;
  pain_points: string[] | null;
  sales_opportunities: string[] | null;
  estimated_revenue: string | null;
  funding_stage: string | null;
  growth_signals: string[] | null;
  data_quality: DataQuality;
  researched_at: string;
  is_stale: boolean;
}

export type BulkCompanyActionType =
  | "delete" | "archive" | "restore" | "assign_owner" | "change_status" | "add_tags" | "remove_tags";

export interface BulkCompanyActionRequest {
  company_ids: string[];
  action: BulkCompanyActionType;
  owner_id?: string;
  status?: string;
  tags?: string[];
}

export interface BulkActionError {
  company_id: string;
  message: string;
}

export interface BulkActionResponse {
  action: string;
  requested_count: number;
  success_count: number;
  failed_count: number;
  errors: BulkActionError[];
}
