"use client";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import { useEmailPreview } from "../hooks/use-lead-sending";

export interface EmailPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  emailId: string | undefined;
}

/** Renders the exact final HTML — including the server-injected compliance
 * footer — sanitized before render, same as the variant review screen. */
export function EmailPreviewDialog({ open, onOpenChange, emailId }: EmailPreviewDialogProps): React.ReactElement {
  const { preview, isLoading } = useEmailPreview(open ? emailId : undefined);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{preview?.subject ?? "Email preview"}</DialogTitle>
          <DialogDescription>
            {preview ? `To ${preview.to_name ? `${preview.to_name} <${preview.to_email}>` : preview.to_email}` : "Loading…"}
          </DialogDescription>
        </DialogHeader>
        {isLoading || !preview ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <div className="max-h-[28rem] overflow-y-auto rounded-lg border border-border bg-card p-4">
            <div
              className="text-body-sm [&_a]:text-primary [&_a]:underline"
              dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(preview.body_html) }}
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
