"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Eye, EyeOff, Send } from "@/icons";
import { useEmailTemplates } from "@/features/email-templates/hooks/use-email-templates";
import { useSenderMailboxes } from "@/features/email-sender/hooks/use-sender-mailboxes";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import { useComposeLeadEmail } from "../hooks/use-lead-sending";
import type { LeadResponse } from "../types";

export interface SendCustomEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead: LeadResponse;
}

/** Phase X Issue 08 — Send Custom Email from Lead Detail: a manual composer
 * independent of both AI generation and campaign sequences. Attachment
 * upload is intentionally out of scope for this pass — it needs its own
 * storage + MIME-encoding-on-send pipeline (the app's mailer currently
 * builds a text/html multipart message only), not a form field; flag it as
 * a follow-up if it's actually needed rather than fake it here. */
export function SendCustomEmailDialog({ open, onOpenChange, lead }: SendCustomEmailDialogProps): React.ReactElement {
  const { mailboxes } = useSenderMailboxes();
  const { templates } = useEmailTemplates({ is_active: true, page_size: 100 });
  const { composeEmail, isComposing } = useComposeLeadEmail();

  const [toEmail, setToEmail] = useState(lead.email ?? "");
  const [toName, setToName] = useState(lead.full_name);
  const [senderMailboxId, setSenderMailboxId] = useState<string>("");
  const [templateId, setTemplateId] = useState<string>("");
  const [subject, setSubject] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [sendNow, setSendNow] = useState(true);
  const [showPreview, setShowPreview] = useState(false);

  function resetForm(): void {
    setToEmail(lead.email ?? "");
    setToName(lead.full_name);
    setSenderMailboxId("");
    setTemplateId("");
    setSubject("");
    setBodyHtml("");
    setBodyText("");
    setSendNow(true);
    setShowPreview(false);
  }

  function handleTemplateChange(value: string): void {
    setTemplateId(value);
    const template = templates.find((t) => t.id === value);
    if (template) {
      setSubject(template.subject);
      setBodyHtml(template.body_html);
      setBodyText(template.body_text ?? "");
    }
  }

  async function handleSubmit(): Promise<void> {
    await composeEmail({
      leadId: lead.id,
      payload: {
        to_email: toEmail || undefined,
        to_name: toName || undefined,
        subject,
        body_html: bodyHtml,
        body_text: bodyText || undefined,
        sender_mailbox_id: senderMailboxId || undefined,
        template_id: templateId || undefined,
        send_now: sendNow,
      },
    });
    resetForm();
    onOpenChange(false);
  }

  const canSubmit = Boolean(toEmail && subject && bodyHtml);

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) resetForm(); onOpenChange(next); }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Send custom email</DialogTitle>
          <DialogDescription>Write a one-off email to {lead.full_name}, independent of AI generation or campaigns.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label>Sender mailbox</Label>
              <Select value={senderMailboxId} onValueChange={setSenderMailboxId}>
                <SelectTrigger>
                  <SelectValue placeholder="Default mailbox" />
                </SelectTrigger>
                <SelectContent>
                  {mailboxes.map((mailbox) => (
                    <SelectItem key={mailbox.id} value={mailbox.id}>
                      {mailbox.name} ({mailbox.email_address})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Start from a template</Label>
              <Select value={templateId} onValueChange={handleTemplateChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Blank email" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label required>Recipient</Label>
              <Input type="email" value={toEmail} onChange={(e) => setToEmail(e.target.value)} placeholder="lead@example.com" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Recipient name</Label>
              <Input value={toName} onChange={(e) => setToName(e.target.value)} />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label required>Subject</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Following up" />
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label required>Body (HTML)</Label>
              <Button type="button" variant="ghost" size="sm" onClick={() => setShowPreview((v) => !v)}>
                {showPreview ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                {showPreview ? "Edit" : "Preview"}
              </Button>
            </div>
            {showPreview ? (
              <div
                className="min-h-40 rounded-md border border-input bg-card p-3 text-body-sm"
                dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(bodyHtml) || "<p class=\"text-muted-foreground\">Nothing to preview yet.</p>" }}
              />
            ) : (
              <Textarea rows={8} value={bodyHtml} onChange={(e) => setBodyHtml(e.target.value)} placeholder="<p>Hi there,</p>" />
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Plain-text fallback</Label>
            <Textarea rows={3} value={bodyText} onChange={(e) => setBodyText(e.target.value)} />
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <p className="text-body-sm font-medium text-foreground">Send immediately</p>
              <p className="text-caption text-muted-foreground">
                {sendNow ? "Sends as soon as you submit." : "Saves as a draft you can review and send later."}
              </p>
            </div>
            <Switch checked={sendNow} onCheckedChange={setSendNow} />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void handleSubmit()} isLoading={isComposing} disabled={!canSubmit}>
            <Send className="size-4" />
            {sendNow ? "Send" : "Save draft"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
