"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { ApiResponse } from "@/types/api";
import { normalizeApiError } from "@/lib/api/errors";
import { organizationService } from "../services/organization.service";
import type { InvitationResponse, InviteUserRequest } from "../types";

const INVITATIONS_QUERY_KEY = ["organizations", "invitations"] as const;

export interface UseInvitationsReturn {
  invitations: InvitationResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  /** Promise-based so callers (e.g. the invite dialog) can `await` + `try/catch` to close on success and surface field errors on failure. */
  inviteUser: (payload: InviteUserRequest) => Promise<ApiResponse<InvitationResponse>>;
  isInviting: boolean;
  revokeInvitation: (invitationId: string) => void;
  isRevoking: boolean;
}

/** Backs the organization invitations panel: list pending invites, send a new one, revoke one. */
export function useInvitations(): UseInvitationsReturn {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: INVITATIONS_QUERY_KEY,
    queryFn: ({ signal }) => organizationService.getInvitations(signal),
  });

  const inviteMutation = useMutation({
    mutationFn: (payload: InviteUserRequest) => organizationService.inviteUser(payload),
    onSuccess: (response) => {
      toast.success(response.message || "Invitation sent.");
      void queryClient.invalidateQueries({ queryKey: INVITATIONS_QUERY_KEY });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (invitationId: string) => organizationService.revokeInvitation(invitationId),
    onSuccess: () => {
      toast.success("Invitation revoked.");
      void queryClient.invalidateQueries({ queryKey: INVITATIONS_QUERY_KEY });
    },
    onError: (error) => {
      toast.error(normalizeApiError(error).message);
    },
  });

  return {
    invitations: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
    inviteUser: (payload) => inviteMutation.mutateAsync(payload),
    isInviting: inviteMutation.isPending,
    revokeInvitation: (invitationId) => revokeMutation.mutate(invitationId),
    isRevoking: revokeMutation.isPending,
  };
}
