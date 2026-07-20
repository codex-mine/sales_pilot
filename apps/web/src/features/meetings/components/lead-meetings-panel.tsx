"use client";

import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Video } from "@/icons";
import { useLeadMeetings } from "../hooks/use-lead-meetings";
import type { MeetingResponse } from "../types";
import { MeetingDetailDrawer } from "./meeting-detail-drawer";
import { MeetingStatusBadge } from "./meeting-status-badge";
import { ScheduleMeetingDialog } from "./schedule-meeting-dialog";

export interface LeadMeetingsPanelProps {
  leadId: string;
}

export function LeadMeetingsPanel({ leadId }: LeadMeetingsPanelProps): React.ReactElement {
  const { meetings, isLoading } = useLeadMeetings(leadId);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [selected, setSelected] = useState<MeetingResponse | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-body-sm text-muted-foreground">{meetings.length} meeting(s)</p>
        <Button size="sm" onClick={() => setScheduleOpen(true)}>
          <Calendar className="size-4" />
          Schedule Meeting
        </Button>
      </div>

      {meetings.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No meetings yet"
          description="Schedule a meeting to propose open times from your connected Google Calendar."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {meetings.map((meeting) => (
            <Card key={meeting.id} className="cursor-pointer transition-colors hover:bg-muted/40" onClick={() => setSelected(meeting)}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <p className="text-body-md font-medium text-foreground">{meeting.title}</p>
                    <MeetingStatusBadge status={meeting.status} />
                  </div>
                  <p className="text-body-sm text-muted-foreground">
                    {meeting.scheduled_start
                      ? formatDistanceToNow(new Date(meeting.scheduled_start), { addSuffix: true })
                      : `${meeting.duration_minutes} min · not yet booked`}
                    {meeting.owner && ` · ${meeting.owner.full_name}`}
                  </p>
                </div>
                {meeting.meeting_url && (
                  <Badge variant="outline">
                    <Video className="size-3" />
                    Google Meet
                  </Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ScheduleMeetingDialog open={scheduleOpen} onOpenChange={setScheduleOpen} leadId={leadId} />
      <MeetingDetailDrawer meeting={selected} open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)} />
    </div>
  );
}
