"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyCreateRequest, CompanyResponse, CompanyUpdateRequest } from "../types";
import { COMPANY_QUERY_KEY } from "./use-company";

export interface UseCreateCompanyReturn {
  createCompany: (payload: CompanyCreateRequest) => Promise<CompanyResponse>;
  isCreating: boolean;
}

export function useCreateCompany(): UseCreateCompanyReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: CompanyCreateRequest) => companyService.createCompany(payload),
    onSuccess: () => {
      toast.success("Company created.");
      void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
    },
  });
  return { createCompany: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateCompanyReturn {
  updateCompany: (args: { companyId: string; payload: CompanyUpdateRequest }) => Promise<CompanyResponse>;
  isUpdating: boolean;
}

export function useUpdateCompany(): UseUpdateCompanyReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ companyId, payload }: { companyId: string; payload: CompanyUpdateRequest }) =>
      companyService.updateCompany(companyId, payload),
    onSuccess: (company) => {
      queryClient.setQueryData(COMPANY_QUERY_KEY(company.id), company);
      void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
      void queryClient.invalidateQueries({ queryKey: ["companies", "activities", company.id] });
    },
  });
  return {
    updateCompany: (args) => mutation.mutateAsync(args),
    isUpdating: mutation.isPending,
  };
}

export interface UseToggleCompanyArchivedReturn {
  toggleArchived: (company: CompanyResponse) => void;
  isToggling: boolean;
}

/** Archive/restore go through dedicated endpoints (not PATCH) — mirrors the backend's explicit archive/restore actions. */
export function useToggleCompanyArchived(): UseToggleCompanyArchivedReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (company: CompanyResponse) =>
      company.is_archived
        ? companyService.restoreCompany(company.id)
        : companyService.archiveCompany(company.id),
    onSuccess: (company) => {
      queryClient.setQueryData(COMPANY_QUERY_KEY(company.id), company);
      void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
      toast.success(company.is_archived ? "Company archived." : "Company restored.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { toggleArchived: (company) => mutation.mutate(company), isToggling: mutation.isPending };
}

export interface UseDeleteCompanyReturn {
  deleteCompany: (companyId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteCompany(): UseDeleteCompanyReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (companyId: string) => companyService.deleteCompany(companyId),
    onSuccess: () => {
      toast.success("Company deleted.");
      void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteCompany: (companyId) => mutation.mutateAsync(companyId), isDeleting: mutation.isPending };
}

export interface UseCompanyLogoReturn {
  uploadLogo: (args: { companyId: string; file: File }) => void;
  isUploading: boolean;
  deleteLogo: (companyId: string) => void;
  isDeleting: boolean;
}

export function useCompanyLogo(): UseCompanyLogoReturn {
  const queryClient = useQueryClient();

  function onSettled(company: CompanyResponse): void {
    queryClient.setQueryData(COMPANY_QUERY_KEY(company.id), company);
    void queryClient.invalidateQueries({ queryKey: ["companies", "list"] });
  }

  const uploadMutation = useMutation({
    mutationFn: ({ companyId, file }: { companyId: string; file: File }) =>
      companyService.uploadCompanyLogo(companyId, file),
    onSuccess: (company) => {
      onSettled(company);
      toast.success("Logo updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (companyId: string) => companyService.deleteCompanyLogo(companyId),
    onSuccess: (company) => {
      onSettled(company);
      toast.success("Logo removed.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    uploadLogo: (args) => uploadMutation.mutate(args),
    isUploading: uploadMutation.isPending,
    deleteLogo: (companyId) => deleteMutation.mutate(companyId),
    isDeleting: deleteMutation.isPending,
  };
}
