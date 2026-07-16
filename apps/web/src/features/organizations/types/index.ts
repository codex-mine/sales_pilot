import type { UserResponse } from "@/features/auth/types";

export type InvitationStatus = "pending" | "accepted" | "expired" | "revoked";

export interface InvitationResponse {
  id: string;
  email: string;
  role_id: string;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
}

export interface RoleResponse {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
}

export interface InviteUserRequest {
  email: string;
  role_id: string;
}

export interface AcceptInvitationRequest {
  token: string;
  first_name: string;
  last_name: string;
  password: string;
}

export type AcceptInvitationResponse = UserResponse;
