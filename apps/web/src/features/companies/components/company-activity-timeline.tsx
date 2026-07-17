"use client";

import { formatDistanceToNow } from "date-fns";
import { Timeline, TimelineItem } from "@/components/ui/timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Archive,
  ArchiveRestore,
  Building2,
  FileText,
  History,
  Link2,
  Tag as TagIcon,
  Trash2,
  Upload,
  UserCog,
  Users,
  type IconComponent,
} from "@/icons";
import { useCompanyActivities } from "../hooks/use-company-activities";
import type { CompanyActivityResponse } from "../types";

const ACTIVITY_META: Record<string, { label: string; icon: IconComponent; tone: "default" | "success" | "warning" | "danger" | "info" | "primary" }> = {
  company_created: { label: "created this company", icon: Building2, tone: "primary" },
  company_updated: { label: "updated this company", icon: FileText, tone: "default" },
  company_archived: { label: "archived this company", icon: Archive, tone: "warning" },
  company_restored: { label: "restored this company", icon: ArchiveRestore, tone: "success" },
  company_deleted: { label: "deleted this company", icon: Trash2, tone: "danger" },
  lead_linked: { label: "linked a lead", icon: Link2, tone: "default" },
  contact_linked: { label: "linked a contact", icon: Users, tone: "default" },
  status_changed: { label: "changed the status", icon: History, tone: "info" },
  owner_changed: { label: "changed the owner", icon: UserCog, tone: "info" },
  tags_changed: { label: "updated tags", icon: TagIcon, tone: "default" },
  note_added: { label: "added a note", icon: FileText, tone: "default" },
  note_updated: { label: "edited a note", icon: FileText, tone: "default" },
  note_deleted: { label: "deleted a note", icon: Trash2, tone: "danger" },
  attachment_uploaded: { label: "uploaded a file", icon: Upload, tone: "default" },
  attachment_deleted: { label: "deleted a file", icon: Trash2, tone: "danger" },
  bulk_action: { label: "applied a bulk action", icon: History, tone: "default" },
};

const DEFAULT_META = { label: "updated this company", icon: History, tone: "default" as const };

function describeActivity(activity: CompanyActivityResponse): { label: string; icon: IconComponent; tone: "default" | "success" | "warning" | "danger" | "info" | "primary" } {
  return ACTIVITY_META[activity.activity_type] ?? DEFAULT_META;
}

export interface CompanyActivityTimelineProps {
  companyId: string;
}

export function CompanyActivityTimeline({ companyId }: CompanyActivityTimelineProps): React.ReactElement {
  const { activities, isLoading } = useCompanyActivities(companyId);

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
    return <EmptyState icon={History} title="No activity yet" description="Actions on this company will show up here." />;
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
