"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { CreateReportRequest, ReportResponse, RunReportResponse, UpdateReportRequest } from "../types";

function invalidateReportLists(queryClient: ReturnType<typeof useQueryClient>): void {
  void queryClient.invalidateQueries({ queryKey: ["reports", "list"] });
}

export interface UseCreateReportReturn {
  createReport: (payload: CreateReportRequest) => Promise<ReportResponse>;
  isCreating: boolean;
}

export function useCreateReport(): UseCreateReportReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: CreateReportRequest) => dashboardService.createReport(payload),
    onSuccess: () => {
      toast.success("Report created.");
      invalidateReportLists(queryClient);
    },
  });
  return { createReport: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateReportReturn {
  updateReport: (args: { reportId: string; payload: UpdateReportRequest }) => Promise<ReportResponse>;
  isUpdating: boolean;
}

export function useUpdateReport(): UseUpdateReportReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ reportId, payload }: { reportId: string; payload: UpdateReportRequest }) =>
      dashboardService.updateReport(reportId, payload),
    onSuccess: () => {
      toast.success("Report updated.");
      invalidateReportLists(queryClient);
    },
  });
  return { updateReport: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteReportReturn {
  deleteReport: (reportId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteReport(): UseDeleteReportReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (reportId: string) => dashboardService.deleteReport(reportId),
    onSuccess: () => {
      toast.success("Report deleted.");
      invalidateReportLists(queryClient);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteReport: (reportId) => mutation.mutateAsync(reportId), isDeleting: mutation.isPending };
}

export interface UseRunReportReturn {
  runReport: (reportId: string) => Promise<RunReportResponse>;
  isRunning: boolean;
}

export function useRunReport(): UseRunReportReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (reportId: string) => dashboardService.runReport(reportId),
    onSuccess: (result) => {
      toast.success(
        result.delivered_to.length > 0
          ? `Report run and emailed to ${result.delivered_to.length} recipient(s).`
          : "Report run.",
      );
      invalidateReportLists(queryClient);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { runReport: (reportId) => mutation.mutateAsync(reportId), isRunning: mutation.isPending };
}
