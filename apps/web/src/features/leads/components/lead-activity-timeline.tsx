"use client";

import { formatDistanceToNow } from "date-fns";
import { Timeline, TimelineItem } from "@/components/ui/timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Archive,
  ArchiveRestore,
  FileText,
  History,
  Star,
  Tag as TagIcon,
  Trash2,
  Upload,
  UserCog,
  type IconComponent,
} from "@/icons";
import { useLeadActivities } from "../hooks/use-lead-activities";
import type { ActivityResponse } from "../types";

const ACTIVITY_META: Record<string, { label: string; icon: IconComponent; tone: "default" | "success" | "warning" | "danger" | "info" | "primary" }> = {
  lead_created: { label: "created this lead", icon: FileText, tone: "primary" },
  lead_updated: { label: "updated this lead", icon: FileText, tone: "default" },
  lead_deleted: { label: "deleted this lead", icon: Trash2, tone: "danger" },
  status_changed: { label: "changed the status", icon: History, tone: "info" },
  owner_changed: { label: "changed the owner", icon: UserCog, tone: "info" },
  tags_changed: { label: "updated tags", icon: TagIcon, tone: "default" },
  note_added: { label: "added a note", icon: FileText, tone: "default" },
  note_updated: { label: "edited a note", icon: FileText, tone: "default" },
  note_deleted: { label: "deleted a note", icon: Trash2, tone: "danger" },
  attachment_uploaded: { label: "uploaded a file", icon: Upload, tone: "default" },
  attachment_deleted: { label: "deleted a file", icon: Trash2, tone: "danger" },
  lead_favorited: { label: "favorited this lead", icon: Star, tone: "warning" },
  lead_unfavorited: { label: "unfavorited this lead", icon: Star, tone: "default" },
  lead_archived: { label: "archived this lead", icon: Archive, tone: "warning" },
  lead_restored: { label: "restored this lead", icon: ArchiveRestore, tone: "success" },
  lead_imported: { label: "imported this lead via CSV", icon: Upload, tone: "primary" },
  bulk_action: { label: "applied a bulk action", icon: History, tone: "default" },
};

const DEFAULT_META = { label: "updated this lead", icon: History, tone: "default" as const };

function describeActivity(activity: ActivityResponse): { label: string; icon: IconComponent; tone: "default" | "success" | "warning" | "danger" | "info" | "primary" } {
  return ACTIVITY_META[activity.activity_type] ?? DEFAULT_META;
}

export interface LeadActivityTimelineProps {
  leadId: string;
}

export function LeadActivityTimeline({ leadId }: LeadActivityTimelineProps): React.ReactElement {
  const { activities, isLoading } = useLeadActivities(leadId);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (activities.length === 0) {
    return <EmptyState icon={History} title="No activity yet" description="Actions on this lead will show up here." />;
  }

  return (
    <Timeline>
      {activities.map((activity, index) => {
        const meta = describeActivity(activity);
        return (
          <TimelineItem
            key={activity.id}
            icon={meta.icon}
            tone={meta.tone}
            isLast={index === activities.length - 1}
            title={
              <>
                {activity.actor_name ?? "System"} <span className="font-normal text-muted-foreground">{meta.label}</span>
              </>
            }
            description={activity.summary}
            timestamp={formatDistanceToNow(new Date(activity.occurred_at), { addSuffix: true })}
          />
        );
      })}
    </Timeline>
  );
}
