"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { meetingService } from "../services/meeting.service";
import type { MeetingResponse, MeetingsQuery, PaginationMeta } from "../types";

export const MEETINGS_QUERY_KEY = (query: MeetingsQuery) => ["meetings", "list", query] as const;

export interface UseMeetingsReturn {
  meetings: MeetingResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useMeetings(query: MeetingsQuery = {}): UseMeetingsReturn {
  const result = useQuery({
    queryKey: MEETINGS_QUERY_KEY(query),
    queryFn: ({ signal }) => meetingService.getMeetings(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    meetings: result.data?.meetings ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
