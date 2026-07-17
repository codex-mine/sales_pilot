"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { formatDistanceToNow } from "date-fns";
import { useForm } from "react-hook-form";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Pin, Trash2 } from "@/icons";
import { getInitials } from "@/lib/utils";
import { useCompanyNotes } from "../hooks/use-company-notes";
import { companyNoteFormSchema, type CompanyNoteFormValues } from "../schemas";

export interface CompanyNotesPanelProps {
  companyId: string;
}

export function CompanyNotesPanel({ companyId }: CompanyNotesPanelProps): React.ReactElement {
  const { notes, isLoading, createNote, isCreating, deleteNote, updateNote } = useCompanyNotes(companyId);

  const form = useForm<CompanyNoteFormValues>({
    resolver: zodResolver(companyNoteFormSchema),
    defaultValues: { content: "", is_pinned: false },
  });

  async function onSubmit(values: CompanyNoteFormValues): Promise<void> {
    await createNote({ content: values.content, isPinned: values.is_pinned });
    form.reset({ content: "", is_pinned: false });
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-2">
        <Textarea rows={3} placeholder="Add a note about this company..." {...form.register("content")} />
        {form.formState.errors.content && (
          <p className="text-body-sm text-danger">{form.formState.errors.content.message}</p>
        )}
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-body-sm text-muted-foreground">
            <Checkbox
              checked={form.watch("is_pinned")}
              onCheckedChange={(checked) => form.setValue("is_pinned", !!checked)}
            />
            Pin this note
          </label>
          <Button type="submit" size="sm" isLoading={isCreating}>
            Add note
          </Button>
        </div>
      </form>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : notes.length === 0 ? (
        <EmptyState icon={FileText} title="No notes yet" description="Notes you add will show up here, newest first." />
      ) : (
        <div className="flex flex-col gap-3">
          {notes.map((note) => (
            <div key={note.id} className="rounded-lg border border-border bg-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Avatar size="xs" fallback={getInitials(note.author_name ?? "?")} />
                  <div className="flex flex-col">
                    <span className="text-body-sm font-medium text-foreground">{note.author_name ?? "Unknown"}</span>
                    <span className="text-caption text-muted-foreground">
                      {formatDistanceToNow(new Date(note.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <IconButton
                    icon={Pin}
                    aria-label={note.is_pinned ? "Unpin note" : "Pin note"}
                    variant={note.is_pinned ? "soft" : "ghost"}
                    size="sm"
                    onClick={() => updateNote({ noteId: note.id, isPinned: !note.is_pinned })}
                  />
                  <IconButton
                    icon={Trash2}
                    aria-label="Delete note"
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteNote(note.id)}
                  />
                </div>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-body-sm text-foreground">{note.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
