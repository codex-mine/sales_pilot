"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { notificationService } from "../services/notification.service";
import type { NotificationResponse } from "../types";

function invalidateNotificationQueries(queryClient: ReturnType<typeof useQueryClient>): void {
  void queryClient.invalidateQueries({ queryKey: ["notifications", "list"] });
  void queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
}

export interface UseMarkNotificationReadReturn {
  markRead: (notificationId: string) => Promise<NotificationResponse>;
  isMarking: boolean;
}

export function useMarkNotificationRead(): UseMarkNotificationReadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (notificationId: string) => notificationService.markNotificationRead(notificationId),
    onSuccess: () => invalidateNotificationQueries(queryClient),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { markRead: (notificationId) => mutation.mutateAsync(notificationId), isMarking: mutation.isPending };
}

export interface UseMarkAllNotificationsReadReturn {
  markAllRead: () => Promise<number>;
  isMarkingAll: boolean;
}

export function useMarkAllNotificationsRead(): UseMarkAllNotificationsReadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => notificationService.markAllNotificationsRead(),
    onSuccess: () => invalidateNotificationQueries(queryClient),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { markAllRead: () => mutation.mutateAsync(), isMarkingAll: mutation.isPending };
}
