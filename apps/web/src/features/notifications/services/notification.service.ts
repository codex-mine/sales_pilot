import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  MarkAllReadResponse,
  NotificationResponse,
  NotificationsQuery,
  PaginationMeta,
  UnreadCountResponse,
} from "../types";

export async function getNotifications(
  query: NotificationsQuery = {},
  signal?: AbortSignal,
): Promise<{ notifications: NotificationResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<NotificationResponse[]>>("/notifications", { params: query, signal });
  return {
    notifications: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getUnreadCount(signal?: AbortSignal): Promise<number> {
  const { data } = await apiClient.get<ApiResponse<UnreadCountResponse>>("/notifications/unread-count", { signal });
  return data.data?.count ?? 0;
}

export async function markNotificationRead(notificationId: string): Promise<NotificationResponse> {
  const { data } = await apiClient.patch<ApiResponse<NotificationResponse>>(`/notifications/${notificationId}/read`);
  if (!data.data) throw new Error("Failed to mark notification read.");
  return data.data;
}

export async function markAllNotificationsRead(): Promise<number> {
  const { data } = await apiClient.post<ApiResponse<MarkAllReadResponse>>("/notifications/read-all");
  return data.data?.marked_count ?? 0;
}

export const notificationService = {
  getNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
};
