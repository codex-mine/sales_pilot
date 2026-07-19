// Mirrors the backend's app/schemas/inbox.py exactly (snake_case, same field names).

export const REPLY_CLASSIFICATION_CHOICES = [
  "interested", "not_interested", "meeting_requested", "needs_follow_up",
  "referral", "out_of_office", "spam", "unsubscribe_request", "unknown",
] as const;
export type ReplyClassification = (typeof REPLY_CLASSIFICATION_CHOICES)[number];

export const REPLY_CLASSIFICATION_LABELS: Record<ReplyClassification, string> = {
  interested: "Interested",
  not_interested: "Not Interested",
  meeting_requested: "Meeting Requested",
  needs_follow_up: "Needs Follow-up",
  referral: "Referral",
  out_of_office: "Out of Office",
  spam: "Spam",
  unsubscribe_request: "Unsubscribe Request",
  unknown: "Unclassified",
};

export interface ConversationListItemResponse {
  id: string;
  lead_id: string;
  lead_full_name: string;
  lead_company_name: string | null;
  subject: string | null;
  message_count: number;
  last_message_at: string | null;
  latest_snippet: string | null;
  latest_direction: "outbound" | "inbound" | null;
  latest_classification: string | null;
  latest_confidence: number | null;
  unread_count: number;
}

export interface ThreadItemResponse {
  id: string;
  direction: "outbound" | "inbound";
  from_email: string;
  from_name: string | null;
  to_email: string | null;
  subject: string | null;
  body_html: string | null;
  body_text: string | null;
  occurred_at: string;
  is_read: boolean | null;
  current_status: string | null;
  reply_classification: string | null;
  ai_suggested_action: string | null;
  ai_confidence: number | null;
}

export interface ConversationDetailResponse {
  id: string;
  lead_id: string;
  lead_full_name: string;
  lead_company_name: string | null;
  subject: string | null;
  is_active: boolean;
  items: ThreadItemResponse[];
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  lead_id: string;
  from_email: string;
  from_name: string | null;
  subject: string | null;
  body_text: string;
  body_html: string | null;
  received_at: string;
  is_read: boolean;
  reply_classification: string | null;
  ai_suggested_action: string | null;
  ai_confidence: number | null;
  ai_classified_at: string | null;
}

export interface ConversationsQuery {
  classification?: string[];
  exclude_classification?: string[];
  unread_only?: boolean;
  owner_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}
