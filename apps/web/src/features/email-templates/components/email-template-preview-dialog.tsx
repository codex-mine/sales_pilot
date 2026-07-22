"use client";

import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import { EMAIL_TEMPLATE_TYPE_LABELS, EMAIL_TONE_LABELS, type EmailTemplateResponse, type EmailTemplateType, type EmailTone } from "../types";

export interface EmailTemplatePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template: EmailTemplateResponse | undefined;
}

/** Renders the raw template content — variables like `{{ lead.first_name }}`
 * are shown literally (unresolved) since a preview has no real lead to
 * interpolate against; this is "what the template looks like," not a
 * personalized send preview. */
export function EmailTemplatePreviewDialog({ open, onOpenChange, template }: EmailTemplatePreviewDialogProps): React.ReactElement | null {
  if (!template) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{template.name}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">
              {EMAIL_TEMPLATE_TYPE_LABELS[template.template_type as EmailTemplateType] ?? template.template_type}
            </Badge>
            {template.tone && <Badge variant="outline">{EMAIL_TONE_LABELS[template.tone as EmailTone] ?? template.tone}</Badge>}
            {template.variables_used?.map((variable) => (
              <Badge key={variable} variant="soft">
                {`{{ ${variable} }}`}
              </Badge>
            ))}
          </div>
          <div className="rounded-lg border border-border">
            <div className="border-b border-border bg-muted/40 px-4 py-2">
              <span className="text-caption text-muted-foreground">Subject</span>
              <p className="text-body-sm font-medium text-foreground">{template.subject}</p>
            </div>
            <div className="max-h-96 overflow-y-auto p-4">
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(template.body_html) }}
              />
            </div>
          </div>
          {template.body_text && (
            <div className="rounded-lg border border-border p-4">
              <span className="text-caption text-muted-foreground">Plain-text fallback</span>
              <p className="whitespace-pre-wrap text-body-sm text-foreground">{template.body_text}</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
