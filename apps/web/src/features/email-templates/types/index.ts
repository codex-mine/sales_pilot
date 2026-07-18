// Mirrors the backend's app/schemas/email_generation.py exactly (snake_case,
// same field names). Tone/template-type choices are shared with the Leads
// module's Email Generation types (re-exported here, not duplicated).
export {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateType,
  type EmailTone,
} from "@/features/leads/types";

export interface EmailTemplateResponse {
  id: string;
  organization_id: string;
  ai_job_id: string | null;
  name: string;
  template_type: string;
  tone: string | null;
  subject: string;
  body_html: string;
  body_text: string | null;
  ai_reasoning: string | null;
  variables_used: string[] | null;
  is_active: boolean;
  is_ai_generated: boolean;
  version: number;
  total_sent: number;
  total_opened: number;
  total_replied: number;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateUpdateRequest {
  name?: string;
  template_type?: string;
  tone?: string;
  subject?: string;
  body_html?: string;
  body_text?: string;
  is_active?: boolean;
}

export interface EmailTemplatesQuery {
  search?: string;
  template_type?: string[];
  tone?: string[];
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}
