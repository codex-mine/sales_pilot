"use client";

import { formatDistanceToNow } from "date-fns";
import { useMemo, useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Pagination } from "@/components/ui/pagination";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchInput } from "@/components/ui/search-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { MessagesSquare } from "@/icons";
import { useOrganizationMembers } from "@/features/organizations/hooks/use-organization-members";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { cn, getInitials } from "@/lib/utils";
import { useConversations } from "../hooks/use-conversations";
import { REPLY_CLASSIFICATION_CHOICES, REPLY_CLASSIFICATION_LABELS } from "../types";
import { ClassificationBadge } from "./classification-badge";

const CLASSIFICATION_OPTIONS: MultiSelectOption[] = REPLY_CLASSIFICATION_CHOICES.map((choice) => ({
  value: choice,
  label: REPLY_CLASSIFICATION_LABELS[choice],
}));

export interface ConversationListProps {
  selectedId: string | undefined;
  onSelect: (conversationId: string) => void;
}

export function ConversationList({ selectedId, onSelect }: ConversationListProps): React.ReactElement {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [classificationFilter, setClassificationFilter] = useState<string[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [ownerId, setOwnerId] = useState<string>("all");
  const [page, setPage] = useState(1);
  const { members } = useOrganizationMembers();

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      classification: classificationFilter.length ? classificationFilter : undefined,
      unread_only: unreadOnly || undefined,
      owner_id: ownerId === "all" ? undefined : ownerId,
      page,
      page_size: 25,
    }),
    [debouncedSearch, classificationFilter, unreadOnly, ownerId, page],
  );

  const { conversations, meta, isLoading } = useConversations(query);
  const pageCount = Math.max(Math.ceil(meta.total / meta.page_size), 1);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-2 border-b border-border p-3">
        <SearchInput
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          onClear={() => setSearch("")}
          placeholder="Search leads or subject..."
        />
        <div className="flex flex-wrap items-center gap-2">
          <MultiSelect
            options={CLASSIFICATION_OPTIONS}
            values={classificationFilter}
            onValuesChange={(values) => {
              setClassificationFilter(values);
              setPage(1);
            }}
            placeholder="All classifications"
            className="min-w-40 flex-1"
          />
          <Select
            value={ownerId}
            onValueChange={(value) => {
              setOwnerId(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Owner" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All owners</SelectItem>
              {members.map((member) => (
                <SelectItem key={member.id} value={member.id}>
                  {member.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <label className="flex items-center gap-2 text-body-sm text-muted-foreground">
          <Switch
            checked={unreadOnly}
            onCheckedChange={(checked) => {
              setUnreadOnly(checked);
              setPage(1);
            }}
          />
          Unread only
        </label>
      </div>

      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState
            icon={MessagesSquare}
            title="No conversations"
            description="Replies from your leads will show up here once they come in."
            className="m-3 min-h-40 border-none"
          />
        ) : (
          <ul className="flex flex-col">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button
                  type="button"
                  onClick={() => onSelect(conversation.id)}
                  className={cn(
                    "flex w-full flex-col gap-1 border-b border-border p-3 text-left transition-colors hover:bg-muted/60",
                    selectedId === conversation.id && "bg-accent",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <Avatar size="xs" fallback={getInitials(conversation.lead_full_name)} />
                      <span
                        className={cn(
                          "truncate text-body-sm text-foreground",
                          conversation.unread_count > 0 && "font-semibold",
                        )}
                      >
                        {conversation.lead_full_name}
                      </span>
                    </div>
                    {conversation.unread_count > 0 && (
                      <span className="flex size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />
                    )}
                  </div>
                  {conversation.latest_snippet && (
                    <p className="truncate text-body-sm text-muted-foreground">{conversation.latest_snippet}</p>
                  )}
                  <div className="flex items-center justify-between gap-2">
                    <ClassificationBadge classification={conversation.latest_classification} />
                    {conversation.last_message_at && (
                      <span className="text-caption text-muted-foreground">
                        {formatDistanceToNow(new Date(conversation.last_message_at), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>

      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <p className="text-caption text-muted-foreground">{meta.total} conversation(s)</p>
        <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />
      </div>
    </div>
  );
}
