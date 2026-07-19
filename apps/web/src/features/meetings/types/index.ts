// Mirrors the backend's app/schemas/meetings.py exactly (snake_case, same field names).

export const MEETING_STATUS_CHOICES = ["proposed", "confirmed", "cancelled", "rescheduled", "completed", "no_show"] as const;
export type MeetingStatus = (typeof MEETING_STATUS_CHOICES)[number];

export const MEETING_STATUS_LABELS: Record<MeetingStatus, string> = {
  proposed: "Proposed",
  confirmed: "Confirmed",
  cancelled: "Cancelled",
  rescheduled: "Rescheduled",
  completed: "Completed",
  no_show: "No-show",
};

export interface ProposedSlot {
  start: string;
  end: string;
}

export interface MeetingOwnerResponse {
  id: string;
  full_name: string;
  email: string;
}

export interface CalendarEventResponse {
  id: string;
  provider: string;
  meet_link: string | null;
  html_link: string | null;
  is_synced: boolean;
}

export interface MeetingResponse {
  id: string;
  organization_id: string;
  lead_id: string;
  lead_full_name: string | null;
  lead_company_name: string | null;
  owner: MeetingOwnerResponse | null;
  title: string;
  description: string | null;
  status: string;
  proposed_times: ProposedSlot[];
  scheduled_start: string | null;
  scheduled_end: string | null;
  duration_minutes: number;
  meeting_url: string | null;
  notes: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  completed_at: string | null;
  calendar_event: CalendarEventResponse | null;
  created_at: string;
}

export interface CreateMeetingRequest {
  title: string;
  description?: string;
  duration_minutes?: number;
  owner_id?: string;
  source_message_id?: string;
}

export interface ProposeTimesRequest {
  slot_count?: number;
}

export interface ProposeTimesResponse {
  meeting: MeetingResponse;
  booking_url: string;
}

export interface RescheduleMeetingRequest {
  new_start: string;
  new_end: string;
}

export interface CancelMeetingRequest {
  reason?: string;
}

export interface LogMeetingOutcomeRequest {
  status: "completed" | "no_show";
  notes?: string;
}

export interface MeetingsQuery {
  status?: string[];
  owner_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

// ─── Public booking page ────────────────────────────────────────────────────────

export interface PublicBookingResponse {
  status: string;
  organization_name: string;
  host_name: string | null;
  title: string;
  description: string | null;
  duration_minutes: number;
  proposed_times: ProposedSlot[];
  scheduled_start: string | null;
  scheduled_end: string | null;
  meeting_url: string | null;
}

export interface ConfirmBookingRequest {
  start: string;
  end: string;
}

export interface ConfirmBookingResponse {
  organization_name: string;
  host_name: string | null;
  title: string;
  scheduled_start: string;
  scheduled_end: string;
  meeting_url: string | null;
}
