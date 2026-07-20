"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { calendarIntegrationService } from "../services/calendar-integration.service";
import type { CalendarConnectionStatusResponse } from "../types";

export const CALENDAR_STATUS_QUERY_KEY = ["calendar-integration", "status"] as const;

export interface UseGoogleCalendarStatusReturn {
  status: CalendarConnectionStatusResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useGoogleCalendarStatus(): UseGoogleCalendarStatusReturn {
  const result = useQuery({
    queryKey: CALENDAR_STATUS_QUERY_KEY,
    queryFn: ({ signal }) => calendarIntegrationService.getCalendarStatus(signal),
  });

  return {
    status: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

/** Navigates the browser to the backend's OAuth `/connect` redirect — there is
 * nothing to await here, the round trip through Google finishes on the
 * `/settings/calendar?calendar_connected=1` redirect target. */
export function useConnectGoogleCalendar(): { connect: () => void } {
  return { connect: () => { window.location.href = calendarIntegrationService.getConnectUrl(); } };
}

export interface UseDisconnectGoogleCalendarReturn {
  disconnect: () => Promise<void>;
  isDisconnecting: boolean;
}

export function useDisconnectGoogleCalendar(): UseDisconnectGoogleCalendarReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => calendarIntegrationService.disconnectCalendar(),
    onSuccess: () => {
      toast.success("Google Calendar disconnected.");
      void queryClient.invalidateQueries({ queryKey: CALENDAR_STATUS_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { disconnect: () => mutation.mutateAsync(), isDisconnecting: mutation.isPending };
}
