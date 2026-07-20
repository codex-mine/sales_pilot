"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { notificationService } from "../services/notification.service";
import type { NotificationResponse, PaginationMeta } from "../types";

export const NOTIFICATIONS_QUERY_KEY = (unreadOnly: boolean, page: number) =>
  ["notifications", "list", unreadOnly, page] as const;

export interface UseNotificationsReturn {
  notifications: NotificationResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useNotifications(unreadOnly = false, page = 1, pageSize = 25): UseNotificationsReturn {
  const result = useQuery({
    queryKey: NOTIFICATIONS_QUERY_KEY(unreadOnly, page),
    queryFn: ({ signal }) => notificationService.getNotifications({ unread_only: unreadOnly, page, page_size: pageSize }, signal),
    placeholderData: (previous) => previous,
  });

  return {
    notifications: result.data?.notifications ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: pageSize, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
