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

// ─── Sender Mailbox Management (multi-mailbox) ────────────────────────────────────

export const ENCRYPTION_TYPE_CHOICES = ["none", "starttls", "ssl"] as const;
export type EncryptionType = (typeof ENCRYPTION_TYPE_CHOICES)[number];

export const ENCRYPTION_TYPE_LABELS: Record<EncryptionType, string> = {
  none: "None",
  starttls: "STARTTLS",
  ssl: "SSL/TLS",
};

export interface TestSmtpConnectionRequest {
  host: string;
  port?: number;
  username?: string;
  password: string;
  encryption_type?: EncryptionType;
}

export interface CreateSenderMailboxRequest {
  name: string;
  email_address: string;
  host: string;
  port?: number;
  username?: string;
  password: string;
  encryption_type?: EncryptionType;
  from_name?: string;
  reply_to?: string;
  is_default?: boolean;
  daily_send_limit?: number;
}

export type UpdateSenderMailboxRequest = Partial<Omit<CreateSenderMailboxRequest, "is_default">> & {
  is_active?: boolean;
};

export interface SenderMailboxResponse {
  id: string;
  name: string;
  email_address: string | null;
  host: string;
  port: number;
  username: string | null;
  encryption_type: string;
  from_name: string | null;
  reply_to: string | null;
  is_default: boolean;
  is_active: boolean;
  daily_send_limit: number | null;
  created_at: string;
  updated_at: string;
}
