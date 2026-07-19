"use client";

import { useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { MessageSquare } from "@/icons";
import { ConversationList } from "./conversation-list";
import { ConversationThread } from "./conversation-thread";

export function InboxPageContent(): React.ReactElement {
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  return (
    <div className="grid h-[calc(100vh-13rem)] min-h-[32rem] grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <ConversationList selectedId={selectedId} onSelect={setSelectedId} />
      </div>
      <div className="overflow-y-auto rounded-lg border border-border bg-card p-4">
        {selectedId ? (
          <ConversationThread conversationId={selectedId} />
        ) : (
          <EmptyState
            icon={MessageSquare}
            title="Select a conversation"
            description="Choose a conversation from the list to read the thread and take action."
            className="h-full min-h-full border-none"
          />
        )}
      </div>
    </div>
  );
}
