"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { organizationService } from "../services/organization.service";
import type { OrganizationDetailResponse, OrganizationMemberResponse } from "../types";
import { ORGANIZATION_DETAIL_QUERY_KEY } from "./use-organization-detail";

export interface UseOrganizationMembersReturn {
  members: OrganizationMemberResponse[];
  total: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

/**
 * The reusable `DataTable` (see components/data-table) does search/sort/
 * pagination client-side over whatever rows it's given, so this fetches one
 * generously-sized page rather than threading server-side paging through the
 * table — consistent with how that component is used everywhere else.
 */
export function useOrganizationMembers(): UseOrganizationMembersReturn {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["organizations", "members"] as const,
    queryFn: async ({ signal }) => {
      const cached = queryClient.getQueryData<OrganizationDetailResponse>(
        ORGANIZATION_DETAIL_QUERY_KEY,
      );
      const organizationId = cached?.id ?? (await organizationService.getCurrentOrganization()).id;
      return organizationService.getOrganizationMembers(
        organizationId,
        { page: 1, page_size: 200, sort_by: "joined_at", sort_desc: true },
        signal,
      );
    },
  });

  return {
    members: query.data?.members ?? [],
    total: query.data?.meta.total ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
  };
}
