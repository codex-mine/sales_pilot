"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { StatusBadge } from "@/components/ui/status-badge";
import { CheckCircle2, Clock3, Eye, Send, Sparkles, X } from "@/icons";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import { useCancelScheduledEmail, useScheduleEmail, useSendEmail } from "../hooks/use-lead-sending";
import type { EmailResponse } from "../types";
import { EmailDeliveryTimeline } from "./email-delivery-timeline";
import { EmailPreviewDialog } from "./email-preview-dialog";
import { EmailScheduleDialog } from "./email-schedule-dialog";

const _DISPATCHED_STATUSES = new Set([
  "sending", "sent", "delivered", "opened", "clicked", "bounced", "failed", "spam",
]);

export interface EmailDraftCardProps {
  leadId: string;
  email: EmailResponse;
}

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  draft: "neutral",
  scheduled: "info",
  sending: "info",
  sent: "success",
  delivered: "success",
  opened: "success",
  clicked: "success",
  bounced: "danger",
  failed: "danger",
  spam: "danger",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Ready to send",
  scheduled: "Scheduled",
  sending: "Sending…",
  sent: "Sent",
  delivered: "Delivered",
  opened: "Opened",
  clicked: "Clicked",
  bounced: "Bounced",
  failed: "Failed",
  spam: "Marked as spam",
};

export function EmailDraftCard({ leadId, email }: EmailDraftCardProps): React.ReactElement {
  const { sendEmail, isSending } = useSendEmail();
  const { scheduleEmail, isScheduling } = useScheduleEmail();
  const { cancelEmail, isCancelling } = useCancelScheduledEmail();
  const sendConfirm = useConfirmDialog();
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  const isDraftOrFailed = email.current_status === "draft" || email.current_status === "failed";

  return (
    <Card>
      <CardContent className="flex flex-col gap-2 pt-6">
        <div className="flex items-center justify-between gap-2">
          <p className="text-body-md font-semibold text-foreground">{email.subject}</p>
          <div className="flex items-center gap-2">
            {email.ai_generated && (
              <Badge variant="soft">
                <Sparkles className="size-3" />
                AI
              </Badge>
            )}
            <StatusBadge tone={STATUS_TONE[email.current_status] ?? "neutral"} pulse={email.current_status === "sending"}>
              {email.current_status !== "sending" && <CheckCircle2 className="size-3" />}
              {STATUS_LABEL[email.current_status] ?? email.current_status}
            </StatusBadge>
          </div>
        </div>
        <p className="text-caption text-muted-foreground">
          From {email.from_name ? `${email.from_name} <${email.from_email}>` : email.from_email} · To{" "}
          {email.to_email}
          {email.current_status === "scheduled" && email.scheduled_at && (
            <> · Scheduled for {new Date(email.scheduled_at).toLocaleString()}</>
          )}
          {email.current_status === "sent" && email.sent_at && (
            <> · Sent {formatDistanceToNow(new Date(email.sent_at), { addSuffix: true })}</>
          )}
        </p>
        <div
          className="rounded-lg border border-border bg-muted/30 p-3 text-body-sm"
          dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(email.body_html) }}
        />

        {_DISPATCHED_STATUSES.has(email.current_status) && (
          <div className="rounded-lg border border-border p-3">
            <EmailDeliveryTimeline emailId={email.id} />
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
          <Button size="sm" variant="ghost" onClick={() => setPreviewOpen(true)}>
            <Eye className="size-4" />
            Preview
          </Button>
          {isDraftOrFailed && (
            <>
              <Button size="sm" onClick={sendConfirm.open} isLoading={isSending}>
                <Send className="size-4" />
                {email.current_status === "failed" ? "Retry" : "Send Now"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setScheduleOpen(true)}>
                <Clock3 className="size-4" />
                Schedule
              </Button>
            </>
          )}
          {email.current_status === "scheduled" && (
            <Button
              size="sm"
              variant="outline"
              className="text-danger"
              onClick={() => void cancelEmail({ leadId, emailId: email.id })}
              isLoading={isCancelling}
            >
              <X className="size-4" />
              Cancel
            </Button>
          )}
        </div>
        {email.current_status === "failed" && (
          <p className="text-body-sm text-danger">This email failed to send — see the Outbox for the reason.</p>
        )}
      </CardContent>

      <ConfirmDialog
        open={sendConfirm.isOpen}
        onOpenChange={sendConfirm.onOpenChange}
        title="Send this email now?"
        description="This sends immediately and cannot be undone."
        confirmLabel="Send now"
        confirmVariant="primary"
        isConfirming={isSending}
        onConfirm={async () => {
          await sendEmail({ leadId, emailId: email.id });
          sendConfirm.close();
        }}
      />
      <EmailScheduleDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        isScheduling={isScheduling}
        onSchedule={async (scheduledAt) => {
          await scheduleEmail({ leadId, emailId: email.id, payload: { scheduled_at: scheduledAt.toISOString() } });
          setScheduleOpen(false);
        }}
      />
      <EmailPreviewDialog open={previewOpen} onOpenChange={setPreviewOpen} emailId={email.id} />
    </Card>
  );
}
