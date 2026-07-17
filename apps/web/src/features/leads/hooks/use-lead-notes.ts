"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { NoteResponse } from "../types";
import { LEAD_QUERY_KEY } from "./use-lead";

const NOTES_QUERY_KEY = (leadId: string) => ["leads", "notes", leadId] as const;

export interface UseLeadNotesReturn {
  notes: NoteResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  createNote: (args: { content: string; isPinned: boolean }) => Promise<NoteResponse>;
  isCreating: boolean;
  updateNote: (args: { noteId: string; content?: string; isPinned?: boolean }) => void;
  deleteNote: (noteId: string) => void;
  isDeleting: boolean;
}

/** Notes for a single lead — invalidates the lead detail query too, since `notes_count` lives there. */
export function useLeadNotes(leadId: string): UseLeadNotesReturn {
  const queryClient = useQueryClient();

  const notesQuery = useQuery({
    queryKey: NOTES_QUERY_KEY(leadId),
    queryFn: ({ signal }) => leadService.getNotes(leadId, signal),
    enabled: Boolean(leadId),
  });

  function invalidate(): void {
    void queryClient.invalidateQueries({ queryKey: NOTES_QUERY_KEY(leadId) });
    void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
  }

  const createMutation = useMutation({
    mutationFn: ({ content, isPinned }: { content: string; isPinned: boolean }) =>
      leadService.createNote(leadId, content, isPinned),
    onSuccess: () => {
      toast.success("Note added.");
      invalidate();
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ noteId, content, isPinned }: { noteId: string; content?: string; isPinned?: boolean }) =>
      leadService.updateNote(leadId, noteId, { content, is_pinned: isPinned }),
    onSuccess: () => invalidate(),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) => leadService.deleteNote(leadId, noteId),
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
