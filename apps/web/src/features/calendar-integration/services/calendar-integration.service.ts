import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type { CalendarConnectionStatusResponse } from "../types";

export async function getCalendarStatus(signal?: AbortSignal): Promise<CalendarConnectionStatusResponse> {
  const { data } = await apiClient.get<ApiResponse<CalendarConnectionStatusResponse>>(
    "/integrations/google-calendar",
    { signal },
  );
  if (!data.data) throw new Error("Calendar status not available.");
  return data.data;
}

/** `/connect` is a server-side redirect into Google's consent screen, not a
 * JSON endpoint — the caller navigates the browser to this URL directly
 * (`window.location.href = ...`) rather than calling it through `apiClient`. */
export function getConnectUrl(): string {
  return apiClient.getUri({ url: "/integrations/google-calendar/connect" });
}

export async function disconnectCalendar(): Promise<void> {
  await apiClient.delete("/integrations/google-calendar");
}

export const calendarIntegrationService = {
  getCalendarStatus,
  getConnectUrl,
  disconnectCalendar,
};
