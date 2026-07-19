// Mirrors the backend's app/schemas/meetings.py CalendarConnectionStatusResponse exactly.

export interface CalendarConnectionStatusResponse {
  is_connected: boolean;
  account_email: string | null;
  connected_at: string | null;
}
