import type { UserResponse } from "@/features/auth/types";
import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  AcceptInvitationRequest,
  InvitationResponse,
  InviteUserRequest,
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

export const organizationService = {
  getInvitations,
  inviteUser,
  revokeInvitation,
  acceptInvitation,
  getRoles,
};
