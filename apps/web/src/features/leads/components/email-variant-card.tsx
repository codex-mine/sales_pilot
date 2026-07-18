"use client";

import { useState } from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Check, Pencil, RefreshCw, Sparkles, Trash2 } from "@/icons";
import type { AIOutputResponse } from "@/features/ai/types";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import {
  useApproveEmailVariant,
  useRegenerateEmailVariant,
  useRejectEmailVariant,
} from "../hooks/use-lead-email-generation";
import type { EmailVariantContent } from "../types";

export interface EmailVariantCardProps {
  leadId: string;
  jobId: string;
  output: AIOutputResponse;
  defaultFromEmail: string;
  defaultFromName: string;
  onApproved: () => void;
}

/** One generated variant, reviewable in isolation: sanitized HTML preview,
 * collapsible AI reasoning, and Approve / Edit-then-Approve / Reject /
 * Regenerate-with-feedback actions — never an auto-send. */
export function EmailVariantCard({
  leadId,
  jobId,
  output,
  defaultFromEmail,
  defaultFromName,
  onApproved,
}: EmailVariantCardProps): React.ReactElement {
  // output_type="email_variant" rows are always a single object (never the
  // raw multi-variant array — that only appears on the chokepoint's own
  // output_type="generate_email" row), so this narrowing is safe.
  const content = (output.content_json ?? {}) as unknown as EmailVariantContent;
  const [mode, setMode] = useState<"view" | "edit" | "regenerate">("view");
  const [subject, setSubject] = useState(content.subject ?? "");
  const [bodyHtml, setBodyHtml] = useState(content.body_html ?? "");
  const [bodyText, setBodyText] = useState(content.body_text ?? "");
  const [fromEmail, setFromEmail] = useState(defaultFromEmail);
  const [fromName, setFromName] = useState(defaultFromName);
  const [saveAsTemplate, setSaveAsTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [feedback, setFeedback] = useState("");

  const { approve, isApproving } = useApproveEmailVariant();
  const { reject, isRejecting } = useRejectEmailVariant();
  const { regenerate, isRegenerating } = useRegenerateEmailVariant();
  const rejectConfirm = useConfirmDialog();

  const isTerminal = output.is_approved !== null;
  const isRejected = output.is_approved === false;

  async function handleApprove(withEdits: boolean): Promise<void> {
    await approve({
      outputId: output.id,
      leadId,
      payload: {
        from_email: fromEmail,
        from_name: fromName || undefined,
        edited_subject: withEdits && subject !== content.subject ? subject : undefined,
        edited_body_html: withEdits && bodyHtml !== content.body_html ? bodyHtml : undefined,
        edited_body_text: withEdits && bodyText !== (content.body_text ?? "") ? bodyText : undefined,
        save_as_template: saveAsTemplate,
        template_name: saveAsTemplate ? templateName || undefined : undefined,
      },
    });
    setMode("view");
    onApproved();
  }

  async function handleReject(): Promise<void> {
    await reject({ outputId: output.id, jobId });
    rejectConfirm.close();
  }

  async function handleRegenerate(): Promise<void> {
    await regenerate({
      leadId,
      payload: { source_output_id: output.id, custom_instruction: feedback, variant_count: 1 },
    });
    setMode("view");
    setFeedback("");
  }

  if (isRejected) {
    return (
      <Card className="opacity-60">
        <CardContent className="flex items-center justify-between gap-3 pt-6">
          <div>
            <p className="text-body-sm font-medium text-foreground line-through">{content.subject}</p>
            <p className="text-caption text-muted-foreground">Rejected</p>
          </div>
          <Badge variant="outline">Rejected</Badge>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {mode === "edit" ? (
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} className="font-medium" />
          ) : (
            <p className="text-body-md font-semibold text-foreground">{content.subject}</p>
          )}
        </div>
        {output.is_approved === true && <Badge variant="success">Approved</Badge>}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {mode === "edit" ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Body (HTML)</Label>
              <Textarea rows={8} value={bodyHtml} onChange={(e) => setBodyHtml(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Plain-text fallback</Label>
              <Textarea rows={4} value={bodyText} onChange={(e) => setBodyText(e.target.value)} />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label required>From email</Label>
                <Input type="email" value={fromEmail} onChange={(e) => setFromEmail(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>From name</Label>
                <Input value={fromName} onChange={(e) => setFromName(e.target.value)} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-body-sm text-muted-foreground">
              <Checkbox checked={saveAsTemplate} onCheckedChange={(checked) => setSaveAsTemplate(!!checked)} />
              Save as a reusable template
            </label>
            {saveAsTemplate && (
              <Input
                placeholder="Template name"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
            )}
          </div>
        ) : mode === "regenerate" ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>What should change?</Label>
              <Textarea
                rows={3}
                placeholder="e.g. make it shorter and more casual"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              />
            </div>
          </div>
        ) : (
          <div
            className="rounded-lg border border-border bg-muted/30 p-4 text-body-sm [&_a]:text-primary [&_a]:underline"
            dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(content.body_html ?? "") }}
          />
        )}

        {content.reasoning && mode === "view" && (
          <Accordion type="single" collapsible>
            <AccordionItem value="reasoning">
              <AccordionTrigger className="text-body-sm text-muted-foreground">
                Why the AI wrote it this way
              </AccordionTrigger>
              <AccordionContent className="text-body-sm text-muted-foreground">{content.reasoning}</AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {!isTerminal && (
          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            {mode === "view" && (
              <>
                <Button size="sm" onClick={() => void handleApprove(false)} isLoading={isApproving}>
                  <Check className="size-4" />
                  Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => setMode("edit")}>
                  <Pencil className="size-4" />
                  Edit then Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => setMode("regenerate")}>
                  <RefreshCw className="size-4" />
                  Regenerate
                </Button>
                <Button size="sm" variant="ghost" className="text-danger" onClick={rejectConfirm.open}>
                  <Trash2 className="size-4" />
                  Reject
                </Button>
              </>
            )}
            {mode === "edit" && (
              <>
                <Button size="sm" onClick={() => void handleApprove(true)} isLoading={isApproving}>
                  <Sparkles className="size-4" />
                  Approve with edits
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setMode("view")}>
                  Cancel
                </Button>
              </>
            )}
            {mode === "regenerate" && (
              <>
                <Button
                  size="sm"
                  onClick={() => void handleRegenerate()}
                  isLoading={isRegenerating}
                  disabled={!feedback.trim()}
                >
                  <RefreshCw className="size-4" />
                  Regenerate with feedback
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setMode("view")}>
                  Cancel
                </Button>
              </>
            )}
          </div>
        )}
      </CardContent>

      <ConfirmDialog
        open={rejectConfirm.isOpen}
        onOpenChange={rejectConfirm.onOpenChange}
        title="Reject this variant?"
        description="This marks the variant as rejected — it won't be approvable afterward. Regenerate instead if you want another attempt."
        confirmLabel="Reject variant"
        isConfirming={isRejecting}
        onConfirm={handleReject}
      />
    </Card>
  );
}
