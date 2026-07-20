"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { CreateDashboardWidgetRequest, DashboardWidgetResponse, UpdateDashboardWidgetRequest } from "../types";
import { DASHBOARD_WIDGETS_QUERY_KEY } from "./use-dashboard-widgets";

export interface UseAddDashboardWidgetReturn {
  addWidget: (payload: CreateDashboardWidgetRequest) => Promise<DashboardWidgetResponse>;
  isAdding: boolean;
}

export function useAddDashboardWidget(): UseAddDashboardWidgetReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: CreateDashboardWidgetRequest) => dashboardService.createDashboardWidget(payload),
    onSuccess: () => {
      toast.success("Widget added.");
      void queryClient.invalidateQueries({ queryKey: DASHBOARD_WIDGETS_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { addWidget: (payload) => mutation.mutateAsync(payload), isAdding: mutation.isPending };
}

export interface UseUpdateDashboardWidgetReturn {
  updateWidget: (args: { widgetId: string; payload: UpdateDashboardWidgetRequest }) => Promise<DashboardWidgetResponse>;
  isUpdating: boolean;
}

export function useUpdateDashboardWidget(): UseUpdateDashboardWidgetReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ widgetId, payload }: { widgetId: string; payload: UpdateDashboardWidgetRequest }) =>
      dashboardService.updateDashboardWidget(widgetId, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: DASHBOARD_WIDGETS_QUERY_KEY }),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateWidget: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseRemoveDashboardWidgetReturn {
  removeWidget: (widgetId: string) => Promise<void>;
  isRemoving: boolean;
}

export function useRemoveDashboardWidget(): UseRemoveDashboardWidgetReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (widgetId: string) => dashboardService.deleteDashboardWidget(widgetId),
    onSuccess: () => {
      toast.success("Widget removed.");
      void queryClient.invalidateQueries({ queryKey: DASHBOARD_WIDGETS_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { removeWidget: (widgetId) => mutation.mutateAsync(widgetId), isRemoving: mutation.isPending };
}
