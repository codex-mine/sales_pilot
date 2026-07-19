"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { EmailEventResponse, EmailTimelineResponse } from "../types";

export const EMAIL_EVENTS_QUERY_KEY = (emailId: string) => ["emails", "events", emailId] as const;
export const EMAIL_TIMELINE_QUERY_KEY = (emailId: string) => ["emails", "timeline", emailId] as const;

export interface UseEmailEventsReturn {
  events: EmailEventResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useEmailEvents(emailId: string | undefined): UseEmailEventsReturn {
  const result = useQuery({
    queryKey: EMAIL_EVENTS_QUERY_KEY(emailId ?? ""),
    queryFn: ({ signal }) => leadService.getEmailEvents(emailId as string, signal),
    enabled: Boolean(emailId),
  });

  return {
    events: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}

export interface UseEmailTimelineReturn {
  timeline: EmailTimelineResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

/** Polls while the email hasn't reached a settled state yet, so the
 * delivery timeline on the Outreach tab updates as open/click/delivery
 * events arrive without a manual refresh. */
export function useEmailTimeline(emailId: string | undefined): UseEmailTimelineReturn {
  const result = useQuery({
    queryKey: EMAIL_TIMELINE_QUERY_KEY(emailId ?? ""),
    queryFn: ({ signal }) => leadService.getEmailTimeline(emailId as string, signal),
    enabled: Boolean(emailId),
    refetchInterval: (query) => {
      const status = query.state.data?.current_status;
      return status && ["sending", "sent", "delivered"].includes(status) ? 15000 : false;
    },
  });

  return {
    timeline: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
