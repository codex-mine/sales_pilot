// Mirrors the backend's app/schemas/email_sending.py exactly (snake_case,
// same field names).

export interface EmailSenderConnectRequest {
  host: string;
  port?: number;
  username?: string;
  password: string;
  use_tls?: boolean;
  daily_send_limit?: number;
}

export interface EmailSenderStatusResponse {
  is_connected: boolean;
  integration_id: string | null;
  host: string | null;
  port: number | null;
  username: string | null;
  use_tls: boolean | null;
  has_platform_fallback: boolean;
  daily_send_limit: number;
  sent_today: number;
}
