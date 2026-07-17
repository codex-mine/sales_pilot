"use client";

import { useRef } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Download, Paperclip, Trash2, Upload } from "@/icons";
import { getMediaUrl } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { useLeadAttachments } from "../hooks/use-lead-attachments";

function formatFileSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface LeadAttachmentsPanelProps {
  leadId: string;
}

export function LeadAttachmentsPanel({ leadId }: LeadAttachmentsPanelProps): React.ReactElement {
  const { attachments, isLoading, uploadAttachment, isUploading, deleteAttachment } = useLeadAttachments(leadId);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) uploadAttachment(file);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-body-sm text-muted-foreground">PDF, DOCX, XLSX, CSV, images, or ZIP. Max 25MB.</p>
        <Button type="button" variant="outline" size="sm" onClick={() => inputRef.current?.click()} isLoading={isUploading}>
          <Upload className="size-4" />
          Upload
        </Button>
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.zip,image/*"
          onChange={handleFileSelected}
        />
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : attachments.length === 0 ? (
        <EmptyState icon={Paperclip} title="No attachments" description="Upload files related to this lead." />
      ) : (
        <div className="flex flex-col gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center gap-3 rounded-md border border-border bg-card p-3"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <Paperclip className="size-4" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-body-sm font-medium text-foreground">{attachment.filename}</span>
                <span className="text-caption text-muted-foreground">
                  {formatFileSize(attachment.file_size)}
                  {attachment.uploaded_by_name && ` · ${attachment.uploaded_by_name}`}
                </span>
              </div>
              <IconButton
                icon={Download}
                aria-label="Download"
                variant="ghost"
                size="sm"
                onClick={() => window.open(getMediaUrl(attachment.file_url), "_blank")}
              />
              <IconButton
                icon={Trash2}
                aria-label="Delete attachment"
                variant="ghost"
                size="sm"
                onClick={() => deleteAttachment(attachment.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
