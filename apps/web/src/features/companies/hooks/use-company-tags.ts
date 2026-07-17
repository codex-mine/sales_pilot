"use client";

import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/company.service";
import type { CompanyTagResponse } from "../types";

export function useCompanyTags(): { tags: CompanyTagResponse[]; isLoading: boolean } {
  const query = useQuery({
    queryKey: ["companies", "tags"] as const,
    queryFn: ({ signal }) => companyService.getCompanyTags(signal),
  });
  return { tags: query.data ?? [], isLoading: query.isLoading };
}
