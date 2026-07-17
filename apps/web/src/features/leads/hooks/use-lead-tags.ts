"use client";

import { useQuery } from "@tanstack/react-query";
import { leadService } from "../services/lead.service";
import type { TagResponse } from "../types";

export function useLeadTags(): { tags: TagResponse[]; isLoading: boolean } {
  const query = useQuery({
    queryKey: ["leads", "tags"] as const,
    queryFn: ({ signal }) => leadService.getLeadTags(signal),
  });
  return { tags: query.data ?? [], isLoading: query.isLoading };
}
