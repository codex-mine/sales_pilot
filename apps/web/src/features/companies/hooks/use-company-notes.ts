"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyNoteResponse } from "../types";
import { COMPANY_QUERY_KEY } from "./use-company";

const NOTES_QUERY_KEY = (companyId: string) => ["companies", "notes", companyId] as const;

export interface UseCompanyNotesReturn {
  notes: CompanyNoteResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  createNote: (args: { content: string; isPinned: boolean }) => Promise<CompanyNoteResponse>;
  isCreating: boolean;
  updateNote: (args: { noteId: string; content?: string; isPinned?: boolean }) => void;
  deleteNote: (noteId: string) => void;
  isDeleting: boolean;
}

/** Notes for a single company — invalidates the company detail query too, since `notes_count` lives there. */
export function useCompanyNotes(companyId: string): UseCompanyNotesReturn {
  const queryClient = useQueryClient();

  const notesQuery = useQuery({
    queryKey: NOTES_QUERY_KEY(companyId),
    queryFn: ({ signal }) => companyService.getCompanyNotes(companyId, signal),
    enabled: Boolean(companyId),
  });

  function invalidate(): void {
    void queryClient.invalidateQueries({ queryKey: NOTES_QUERY_KEY(companyId) });
    void queryClient.invalidateQueries({ queryKey: COMPANY_QUERY_KEY(companyId) });
  }

  const createMutation = useMutation({
    mutationFn: ({ content, isPinned }: { content: string; isPinned: boolean }) =>
      companyService.createCompanyNote(companyId, content, isPinned),
    onSuccess: () => {
      toast.success("Note added.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ noteId, content, isPinned }: { noteId: string; content?: string; isPinned?: boolean }) =>
      companyService.updateCompanyNote(companyId, noteId, { content, is_pinned: isPinned }),
    onSuccess: () => invalidate(),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) => companyService.deleteCompanyNote(companyId, noteId),
    onSuccess: () => {
      toast.success("Note deleted.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    notes: notesQuery.data ?? [],
    isLoading: notesQuery.isLoading,
    isError: notesQuery.isError,
    errorMessage: notesQuery.error ? normalizeApiError(notesQuery.error).message : null,
    createNote: (args) => createMutation.mutateAsync(args),
    isCreating: createMutation.isPending,
    updateNote: (args) => updateMutation.mutate(args),
    deleteNote: (noteId) => deleteMutation.mutate(noteId),
    isDeleting: deleteMutation.isPending,
  };
}
