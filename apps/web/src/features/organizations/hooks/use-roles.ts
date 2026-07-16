"use client";

import { useQuery } from "@tanstack/react-query";
import { organizationService } from "../services/organization.service";
import type { RoleResponse } from "../types";

const ROLES_QUERY_KEY = ["organizations", "roles"] as const;

export interface UseRolesReturn {
  roles: RoleResponse[];
  isLoading: boolean;
  isError: boolean;
}

/** The current org's assignable roles — powers the invite-member role picker. */
export function useRoles(): UseRolesReturn {
  const query = useQuery({
    queryKey: ROLES_QUERY_KEY,
    queryFn: ({ signal }) => organizationService.getRoles(signal),
    staleTime: 5 * 60_000,
  });

  return { roles: query.data ?? [], isLoading: query.isLoading, isError: query.isError };
}
