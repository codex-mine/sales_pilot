import type { UserResponse } from "@/features/auth/types";
import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  AcceptInvitationRequest,
  InvitationResponse,
  InviteUserRequest,
  OrganizationDetailResponse,
  OrganizationMembersQuery,
  OrganizationMemberResponse,
  OrganizationUpdateRequest,
  PaginationMeta,
  RoleResponse,
} from "../types";

export async function getInvitations(signal?: AbortSignal): Promise<InvitationResponse[]> {
  const { data } = await apiClient.get<ApiResponse<InvitationResponse[]>>(
    "/organizations/invitations",
    { signal },
  );
  return data.data ?? [];
}

export async function inviteUser(payload: InviteUserRequest): Promise<ApiResponse<InvitationResponse>> {
  const { data } = await apiClient.post<ApiResponse<InvitationResponse>>(
    "/organizations/invitations",
    payload,
  );
  return data;
}

export async function revokeInvitation(invitationId: string): Promise<void> {
  await apiClient.delete(`/organizations/invitations/${invitationId}`);
}

export async function acceptInvitation(
  payload: AcceptInvitationRequest,
): Promise<ApiResponse<UserResponse>> {
  const { data } = await apiClient.post<ApiResponse<UserResponse>>(
    "/organizations/invitations/accept",
    payload,
  );
  return data;
}

export async function getRoles(signal?: AbortSignal): Promise<RoleResponse[]> {
  const { data } = await apiClient.get<ApiResponse<RoleResponse[]>>("/organizations/roles", {
    signal,
  });
  return data.data ?? [];
}

// ─── Organization CRUD / settings / members ────────────────────────────────────

export async function getCurrentOrganization(signal?: AbortSignal): Promise<OrganizationDetailResponse> {
  const { data } = await apiClient.get<ApiResponse<OrganizationDetailResponse>>(
    "/organizations/current",
    { signal },
  );
  if (!data.data) throw new Error("Organization not found.");
  return data.data;
}

export async function updateOrganization(
  organizationId: string,
  payload: OrganizationUpdateRequest,
): Promise<OrganizationDetailResponse> {
  const { data } = await apiClient.patch<ApiResponse<OrganizationDetailResponse>>(
    `/organizations/${organizationId}`,
    payload,
  );
  if (!data.data) throw new Error("Organization update failed.");
  return data.data;
}

export async function deleteOrganization(organizationId: string): Promise<void> {
  await apiClient.delete(`/organizations/${organizationId}`);
}

export async function uploadOrganizationLogo(
  organizationId: string,
  file: File,
): Promise<OrganizationDetailResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<ApiResponse<OrganizationDetailResponse>>(
    `/organizations/${organizationId}/logo`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  if (!data.data) throw new Error("Logo upload failed.");
  return data.data;
}

export async function deleteOrganizationLogo(organizationId: string): Promise<OrganizationDetailResponse> {
  const { data } = await apiClient.delete<ApiResponse<OrganizationDetailResponse>>(
    `/organizations/${organizationId}/logo`,
  );
  if (!data.data) throw new Error("Logo removal failed.");
  return data.data;
}

export async function getOrganizationMembers(
  organizationId: string,
  query: OrganizationMembersQuery = {},
  signal?: AbortSignal,
): Promise<{ members: OrganizationMemberResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<OrganizationMemberResponse[]>>(
    `/organizations/${organizationId}/members`,
    { params: query, signal },
  );
  return {
    members: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 50, total: 0 },
  };
}

export const organizationService = {
  getInvitations,
  inviteUser,
  revokeInvitation,
  acceptInvitation,
  getRoles,
  getCurrentOrganization,
  updateOrganization,
  deleteOrganization,
  uploadOrganizationLogo,
  deleteOrganizationLogo,
  getOrganizationMembers,
};
