// Mirrors the backend's app/schemas/ai.py exactly (snake_case, same field names).

export const LLM_PROVIDER_CHOICES = ["openai", "anthropic", "groq", "google", "mistral", "local"] as const;
export type LLMProvider = (typeof LLM_PROVIDER_CHOICES)[number];

export const LLM_PROVIDER_LABELS: Record<LLMProvider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  groq: "Groq",
  google: "Gemini",
  mistral: "Mistral",
  local: "Ollama",
};

export const AI_AGENT_TYPE_CHOICES = [
  "orchestrator",
  "research",
  "prospect_analysis",
  "email_generation",
  "reply_analysis",
  "meeting",
  "crm",
  "analytics",
] as const;
export type AIAgentType = (typeof AI_AGENT_TYPE_CHOICES)[number];

export const AI_AGENT_TYPE_LABELS: Record<AIAgentType, string> = {
  orchestrator: "Orchestrator",
  research: "Company Research",
  prospect_analysis: "Prospect Analysis",
  email_generation: "Email Generation",
  reply_analysis: "Reply Analysis",
  meeting: "Meeting Detection",
  crm: "CRM",
  analytics: "Analytics",
};

export const AI_JOB_STATUS_CHOICES = [
  "pending",
  "running",
  "completed",
  "failed",
  "retrying",
  "cancelled",
] as const;
export type AIJobStatus = (typeof AI_JOB_STATUS_CHOICES)[number];

// ─── Agents ──────────────────────────────────────────────────────────────────

export interface AIAgentResponse {
  id: string;
  organization_id: string;
  name: string;
  agent_type: string;
  description: string | null;
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  prompt_template_id: string | null;
  prompt_template_name: string | null;
  is_active: boolean;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AIAgentCreateRequest {
  name: string;
  agent_type: AIAgentType;
  description?: string;
  provider?: LLMProvider;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
  prompt_template_id?: string;
  is_active?: boolean;
  config?: Record<string, unknown>;
}

export type AIAgentUpdateRequest = Partial<Omit<AIAgentCreateRequest, "agent_type">>;

// ─── Jobs / outputs ──────────────────────────────────────────────────────────

export interface AIOutputResponse {
  id: string;
  job_id: string;
  output_type: string;
  content_text: string | null;
  content_json: Record<string, unknown> | unknown[] | null;
  is_approved: boolean | null;
  approved_by: string | null;
  approved_at: string | null;
  quality_score: number | null;
  created_at: string;
}

export interface AIJobResponse {
  id: string;
  organization_id: string;
  agent_id: string | null;
  agent_type: string | null;
  parent_job_id: string | null;
  initiated_by: string | null;
  entity_type: string | null;
  entity_id: string | null;
  job_type: string;
  status: AIJobStatus;
  provider: string | null;
  model_name: string | null;
  prompt_version_id: string | null;
  input_data: Record<string, unknown> | null;
  error_message: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  retry_count: number;
  max_retries: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  outputs: AIOutputResponse[];
}

export interface AIJobListItemResponse {
  id: string;
  job_type: string;
  status: AIJobStatus;
  entity_type: string | null;
  entity_id: string | null;
  provider: string | null;
  model_name: string | null;
  total_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  retry_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AIJobsQuery {
  status?: AIJobStatus[];
  job_type?: string[];
  entity_type?: string;
  entity_id?: string;
  created_from?: string;
  created_to?: string;
  page?: number;
  page_size?: number;
}

// ─── Prompts ─────────────────────────────────────────────────────────────────

export interface PromptTemplateResponse {
  id: string;
  organization_id: string;
  name: string;
  agent_type: string | null;
  description: string | null;
  is_system: boolean;
  active_version_id: string | null;
  active_version_number: number | null;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface PromptVersionResponse {
  id: string;
  template_id: string;
  version_number: number;
  system_prompt: string;
  user_prompt_template: string;
  variables: string[];
  provider: string | null;
  model_name: string | null;
  temperature: number | null;
  change_notes: string | null;
  is_active: boolean;
  total_uses: number;
  created_at: string;
}

export interface PromptTemplateCreateRequest {
  name: string;
  agent_type?: AIAgentType;
  description?: string;
  system_prompt: string;
  user_prompt_template: string;
  variables?: string[];
}

export interface PromptTemplateUpdateRequest {
  name?: string;
  description?: string;
}

export interface PromptVersionCreateRequest {
  system_prompt: string;
  user_prompt_template: string;
  variables?: string[];
  provider?: LLMProvider;
  model_name?: string;
  temperature?: number;
  change_notes?: string;
  activate?: boolean;
}

// ─── Settings / usage ────────────────────────────────────────────────────────

export interface AIProviderStatusResponse {
  provider: string;
  integration_type: string;
  has_key: boolean;
  has_org_key: boolean;
  has_platform_fallback: boolean;
}

export interface AISettingsResponse {
  providers: AIProviderStatusResponse[];
  default_provider: string;
  default_model: string;
}

export interface AISettingsUpdateRequest {
  provider: LLMProvider;
  api_key?: string;
  base_url?: string;
  remove?: boolean;
}

export interface AIUsageByJobTypeResponse {
  job_type: string;
  job_count: number;
  total_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface AIDailyCostResponse {
  date: string;
  cost_usd: number;
}

export interface AIUsageResponse {
  window_days: number;
  total_cost_usd: number;
  total_jobs: number;
  total_tokens: number;
  all_time_cost_usd: number;
  by_job_type: AIUsageByJobTypeResponse[];
  daily_costs: AIDailyCostResponse[];
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

// Job statuses that mean "still working" — hooks polling job status stop
// refetching once the status leaves this set.
export const ACTIVE_JOB_STATUSES: ReadonlySet<AIJobStatus> = new Set(["pending", "running", "retrying"]);
