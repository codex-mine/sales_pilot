"use client";

import { useQuery } from "@tanstack/react-query";
import { notificationService } from "../services/notification.service";

const POLL_INTERVAL_MS = 45_000;

export interface UseUnreadNotificationCountReturn {
  count: number;
  isLoading: boolean;
}

/** Polls at a fixed interval rather than pushing over a socket — no
 * WebSocket/SSE layer exists elsewhere in the app, so this stays consistent
 * with that scope. 45s balances a responsive-feeling bell badge against
 * needless request volume for a low-urgency number. */
export function useUnreadNotificationCount(): UseUnreadNotificationCountReturn {
  const result = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: ({ signal }) => notificationService.getUnreadCount(signal),
    refetchInterval: POLL_INTERVAL_MS,
  });

  return { count: result.data ?? 0, isLoading: result.isLoading };
}
