"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { PipelineFunnelResponse } from "../types";

export interface UsePipelineFunnelReturn {
  funnel: PipelineFunnelResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function usePipelineFunnel(): UsePipelineFunnelReturn {
  const result = useQuery({
    queryKey: ["dashboard", "pipeline-funnel"],
    queryFn: ({ signal }) => dashboardService.getPipelineFunnel(signal),
  });

  return {
    funnel: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
