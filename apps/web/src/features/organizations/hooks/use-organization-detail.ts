"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { organizationService } from "../services/organization.service";
import type { OrganizationDetailResponse } from "../types";

export const ORGANIZATION_DETAIL_QUERY_KEY = ["organizations", "current"] as const;

export interface UseOrganizationDetailReturn {
  organization: OrganizationDetailResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** Full profile/settings shape for the current organization (richer than the auth store's minimal `organization`). Backs the Organization module's detail/settings/members pages. */
export function useOrganizationDetail(): UseOrganizationDetailReturn {
  const query = useQuery({
    queryKey: ORGANIZATION_DETAIL_QUERY_KEY,
    queryFn: ({ signal }) => organizationService.getCurrentOrganization(signal),
  });

  return {
    organization: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
    refetch: () => void query.refetch(),
  };
}

/** List-shaped wrapper around the same data — every user belongs to exactly one organization today (see backend docstring), so this is always a 0-or-1-item array. */
export function useOrganizations(): { organizations: OrganizationDetailResponse[]; isLoading: boolean } {
  const { organization, isLoading } = useOrganizationDetail();
  return { organizations: organization ? [organization] : [], isLoading };
}
