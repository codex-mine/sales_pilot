"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { authService } from "@/features/auth/services/auth.service";
import { normalizeApiError } from "@/lib/api/errors";
import type { SessionResponse } from "../types";

const SESSIONS_QUERY_KEY = ["auth", "sessions"] as const;

export interface UseSessionReturn {
  sessions: SessionResponse[];
  currentSession: SessionResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
  revokeSession: (sessionId: string) => void;
  isRevoking: boolean;
}

/** Backs the "Active Sessions" settings panel: list + per-session revoke. */
export function useSession(): UseSessionReturn {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: SESSIONS_QUERY_KEY,
    queryFn: ({ signal }) => authService.getSessions(signal),
  });

  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => authService.revokeSession(sessionId),
    onSuccess: () => {
      toast.success("Session revoked.");
      void queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    },
    onError: (error) => {
      toast.error(normalizeApiError(error).message);
    },
  });

  const sessions = query.data ?? [];

  return {
    sessions,
    currentSession: sessions.find((session) => session.is_current),
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
    refetch: () => void query.refetch(),
    revokeSession: (sessionId: string) => revokeMutation.mutate(sessionId),
    isRevoking: revokeMutation.isPending,
  };
}
