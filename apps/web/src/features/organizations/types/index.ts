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

// ─── Organization CRUD / settings / members ────────────────────────────────────

export const COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"] as const;
export type CompanySize = (typeof COMPANY_SIZES)[number];

export interface OrganizationAddress {
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
}

export interface OrganizationDetailResponse {
  id: string;
  name: string;
  slug: string;
  domain: string | null;
  logo_url: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  industry: string | null;
  country: string | null;
  company_size: string | null;
  timezone: string;
  language: string;
  currency: string;
  brand_color: string | null;
  description: string | null;
  address: OrganizationAddress | null;
  is_active: boolean;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdateRequest {
  name?: string;
  slug?: string;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  industry?: string | null;
  country?: string | null;
  company_size?: string | null;
  description?: string | null;
  timezone?: string;
  language?: string;
  currency?: string;
  brand_color?: string | null;
  address?: OrganizationAddress | null;
}

export type OrganizationMemberStatus =
  | "pending_verification"
  | "active"
  | "suspended"
  | "disabled"
  | "inactive"
  | "deleted";

export interface OrganizationMemberResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  avatar_url: string | null;
  role: string | null;
  status: OrganizationMemberStatus;
  email_verified: boolean;
  joined_at: string;
  last_active_at: string | null;
}

export interface OrganizationMembersQuery {
  search?: string;
  status?: string;
  role?: string;
  sort_by?: "name" | "email" | "status" | "joined_at" | "last_active_at";
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}
