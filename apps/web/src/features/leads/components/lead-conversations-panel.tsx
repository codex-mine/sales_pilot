"use client";

import { formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { MessagesSquare } from "@/icons";
import { ClassificationBadge } from "@/features/inbox/components/classification-badge";
import { ConversationThread } from "@/features/inbox/components/conversation-thread";
import { useLeadConversations } from "@/features/inbox/hooks/use-lead-conversations";

export interface LeadConversationsPanelProps {
  leadId: string;
}

/** The Lead Detail "Conversations" tab — reuses the same `ConversationThread`
 * the standalone Inbox page renders, scoped to this lead's conversations. */
export function LeadConversationsPanel({ leadId }: LeadConversationsPanelProps): React.ReactElement {
  const { conversations, isLoading } = useLeadConversations(leadId);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!selectedId && conversations.length > 0) {
      setSelectedId(conversations[0]!.id);
    }
  }, [conversations, selectedId]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <EmptyState
        icon={MessagesSquare}
        title="No conversations yet"
        description="Replies from this lead will show up here once they come in."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {conversations.length > 1 && (
        <Select value={selectedId} onValueChange={setSelectedId}>
          <SelectTrigger className="w-full sm:w-80">
            <SelectValue placeholder="Select a conversation" />
          </SelectTrigger>
          <SelectContent>
            {conversations.map((conversation) => (
              <SelectItem key={conversation.id} value={conversation.id}>
                <span className="flex items-center gap-2">
                  {conversation.subject || "(no subject)"}
                  {conversation.last_message_at && (
                    <span className="text-caption text-muted-foreground">
                      · {formatDistanceToNow(new Date(conversation.last_message_at), { addSuffix: true })}
                    </span>
                  )}
                  <ClassificationBadge classification={conversation.latest_classification} />
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {selectedId && <ConversationThread conversationId={selectedId} hideLeadHeader />}
    </div>
  );
}
