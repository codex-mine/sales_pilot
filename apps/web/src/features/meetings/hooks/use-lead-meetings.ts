"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { meetingService } from "../services/meeting.service";
import type { MeetingResponse } from "../types";

export const LEAD_MEETINGS_QUERY_KEY = (leadId: string) => ["meetings", "lead", leadId] as const;

export interface UseLeadMeetingsReturn {
  meetings: MeetingResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useLeadMeetings(leadId: string | undefined): UseLeadMeetingsReturn {
  const result = useQuery({
    queryKey: LEAD_MEETINGS_QUERY_KEY(leadId ?? ""),
    queryFn: ({ signal }) => meetingService.getLeadMeetings(leadId as string, signal),
    enabled: Boolean(leadId),
  });

  return {
    meetings: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
