/**
 * Types mirroring the backend's `app.schemas.auth` Pydantic models exactly
 * (field names included — snake_case, matching the wire format). Do not
 * rename fields to camelCase here; that mapping, if ever wanted, belongs at
 * the UI layer, not in the contract types themselves.
 */

export type AccountStatus =
  | "pending_verification"
  | "active"
  | "inactive"
  | "suspended"
  | "disabled"
  | "deleted";

export interface UserResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email_verified: boolean;
  status: AccountStatus;
  organization_id: string;
  role: string | null;
  roles: string[];
  avatar_url: string | null;
  last_login_at: string | null;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  timezone: string;
  is_active: boolean;
}

export interface MeResponse {
  user: UserResponse;
  organization: OrganizationResponse;
  workspace: OrganizationResponse;
  permissions: string[];
}

export interface SessionDeviceInfo {
  browser?: string;
  browser_version?: string;
  os?: string;
  os_version?: string;
  device?: string;
  is_mobile?: boolean;
  is_tablet?: boolean;
  is_pc?: boolean;
  is_bot?: boolean;
}

export interface SessionResponse {
  id: string;
  ip_address: string | null;
  device: SessionDeviceInfo | null;
  is_current: boolean;
  created_at: string;
  last_active_at: string;
  expires_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ─── Requests ──────────────────────────────────────────────────────────────────

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  organization_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember_me: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface VerifyEmailRequest {
  token: string;
}
