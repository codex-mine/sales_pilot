"use client";

import { formatDistanceToNow } from "date-fns";
import { useEffect, useRef, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Calendar, Sparkles } from "@/icons";
import { ScheduleMeetingDialog } from "@/features/meetings/components/schedule-meeting-dialog";
import { sanitizeEmailHtml } from "@/lib/sanitize-html";
import { cn, getInitials } from "@/lib/utils";
import { useConversation, useMarkConversationRead } from "../hooks/use-conversation";
import { useReclassifyMessage } from "../hooks/use-message";
import { REPLY_CLASSIFICATION_CHOICES, REPLY_CLASSIFICATION_LABELS, type ThreadItemResponse } from "../types";
import { ClassificationBadge } from "./classification-badge";

export interface ConversationThreadProps {
  conversationId: string;
  /** Hides the lead name/company header line — the Lead Detail tab already shows it above. */
  hideLeadHeader?: boolean;
}

/** The merged outbound(Email)/inbound(Message) thread view — shared between the
 * standalone Inbox page and the Lead Detail "Conversations" tab. */
export function ConversationThread({ conversationId, hideLeadHeader }: ConversationThreadProps): React.ReactElement {
  const { conversation, isLoading, isError, errorMessage, refetch } = useConversation(conversationId);
  const { markConversationRead } = useMarkConversationRead();
  const markedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!conversation || markedRef.current === conversation.id) return;
    const hasUnread = conversation.items.some((item) => item.direction === "inbound" && item.is_read === false);
    if (hasUnread) {
      markedRef.current = conversation.id;
      void markConversationRead({ conversationId: conversation.id, isRead: true });
    }
  }, [conversation, markConversationRead]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError || !conversation) {
    return <ErrorState title="Couldn't load conversation" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  return (
    <div className="flex flex-col gap-4">
      {!hideLeadHeader && (
        <div className="flex flex-col gap-0.5 border-b border-border pb-3">
          <p className="text-body-md font-semibold text-foreground">{conversation.subject || "(no subject)"}</p>
          <p className="text-body-sm text-muted-foreground">
            {conversation.lead_full_name}
            {conversation.lead_company_name && ` · ${conversation.lead_company_name}`}
          </p>
        </div>
      )}
      <div className="flex flex-col gap-3">
        {conversation.items.map((item) => (
          <ThreadItemCard key={`${item.direction}-${item.id}`} item={item} leadId={conversation.lead_id} />
        ))}
      </div>
    </div>
  );
}

function ThreadItemCard({ item, leadId }: { item: ThreadItemResponse; leadId: string }): React.ReactElement {
  const isInbound = item.direction === "inbound";
  const { reclassifyMessage, isReclassifying } = useReclassifyMessage();
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const confirmSuppress = useConfirmDialog();
  const [pendingClassification, setPendingClassification] = useState<string | null>(null);

  function applyClassification(next: string): void {
    reclassifyMessage({ messageId: item.id, classification: next }).catch(() => {
      // toasted in the mutation's onError
    });
  }

  function handleClassificationChange(next: string): void {
    if (next === item.reply_classification) return;
    if (next === "unsubscribe_request") {
      setPendingClassification(next);
      confirmSuppress.open();
      return;
    }
    applyClassification(next);
  }

  function handleConfirmSuppress(): void {
    if (pendingClassification) applyClassification(pendingClassification);
    confirmSuppress.close();
    setPendingClassification(null);
  }

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-4",
        isInbound ? "border-border bg-card" : "border-transparent bg-muted/40",
      )}
    >
      <Avatar size="sm" fallback={getInitials(item.from_name || item.from_email)} />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-body-sm font-medium text-foreground">
              {item.from_name || item.from_email}
            </span>
            <Badge variant="outline">{isInbound ? "Reply" : "Sent"}</Badge>
          </div>
          <span className="text-caption text-muted-foreground">
            {formatDistanceToNow(new Date(item.occurred_at), { addSuffix: true })}
          </span>
        </div>

        {item.body_html ? (
          <div
            className="rounded-md border border-border bg-background p-3 text-body-sm"
            dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(item.body_html) }}
          />
        ) : (
          <p className="whitespace-pre-wrap rounded-md border border-border bg-background p-3 text-body-sm text-foreground">
            {item.body_text}
          </p>
        )}

        {isInbound && (
          <div className="flex flex-col gap-2">
            {item.reply_classification ? (
              <div className="flex flex-wrap items-center gap-2">
                <ClassificationBadge classification={item.reply_classification} />
                {item.ai_confidence != null && (
                  <span className="text-caption text-muted-foreground">
                    {Math.round(item.ai_confidence * 100)}% confidence
                  </span>
                )}
              </div>
            ) : (
              // No job id is surfaced on Message to drive the full
              // AgentStepTimeline here (see useConversation's
              // hasPendingClassification) — a brief pulsing label instead of
              // a blank wait while the reply_agent graph classifies.
              <StatusBadge tone="info" pulse>
                Classifying reply…
              </StatusBadge>
            )}

            {item.ai_suggested_action && (
              <Alert variant="info" icon={Sparkles}>
                <AlertTitle>AI suggested action</AlertTitle>
                <AlertDescription>{item.ai_suggested_action}</AlertDescription>
              </Alert>
            )}

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Select
                value={item.reply_classification ?? undefined}
                onValueChange={handleClassificationChange}
                disabled={isReclassifying}
              >
                <SelectTrigger className="w-56">
                  <SelectValue placeholder="Classify reply..." />
                </SelectTrigger>
                <SelectContent>
                  {REPLY_CLASSIFICATION_CHOICES.map((choice) => (
                    <SelectItem key={choice} value={choice}>
                      {REPLY_CLASSIFICATION_LABELS[choice]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {(item.reply_classification === "meeting_requested" || item.reply_classification === "interested") && (
                <Button variant="outline" size="sm" onClick={() => setScheduleOpen(true)}>
                  <Calendar className="size-4" />
                  Create Meeting
                </Button>
              )}
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmSuppress.isOpen}
        onOpenChange={(open) => {
          confirmSuppress.onOpenChange(open);
          if (!open) setPendingClassification(null);
        }}
        title="Reclassify as unsubscribe request?"
        description="This will suppress the lead — no further emails will be sent to them, matching how an unsubscribe-link click or a spam complaint is handled."
        confirmLabel="Reclassify & suppress"
        isConfirming={isReclassifying}
        onConfirm={handleConfirmSuppress}
      />
      <ScheduleMeetingDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        leadId={leadId}
        sourceMessageId={item.id}
        defaultTitle={item.subject ? `Re: ${item.subject}` : "Intro call"}
      />
    </div>
  );
}
