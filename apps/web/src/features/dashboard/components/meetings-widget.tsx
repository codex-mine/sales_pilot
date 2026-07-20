"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CalendarDays } from "@/icons";
import type { MeetingsSummary } from "../types";

export interface MeetingsWidgetProps {
  meetings: MeetingsSummary | undefined;
  isLoading: boolean;
}

export function MeetingsWidget({ meetings, isLoading }: MeetingsWidgetProps): React.ReactElement {
  const upcoming = meetings?.upcoming ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarDays className="size-4" />
          Meetings
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading ? (
          <>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </>
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <span className="text-heading-5 font-semibold text-foreground">{meetings?.booked_this_month ?? 0}</span>
              <span className="text-body-sm text-muted-foreground">booked this month</span>
            </div>
            {upcoming.length === 0 ? (
              <p className="py-4 text-center text-body-sm text-muted-foreground">No meetings scheduled this week.</p>
            ) : (
              <div className="flex flex-col gap-1">
                {upcoming.map((meeting) => (
                  <Link
                    key={meeting.id}
                    href={`/meetings?meeting=${meeting.id}`}
                    className="flex items-center justify-between gap-3 rounded-md px-2 py-2 hover:bg-muted/60"
                  >
                    <div className="flex min-w-0 flex-col">
                      <span className="truncate text-body-sm font-medium text-foreground">{meeting.title}</span>
                      {meeting.lead_full_name && (
                        <span className="truncate text-caption text-muted-foreground">{meeting.lead_full_name}</span>
                      )}
                    </div>
                    {meeting.scheduled_start && (
                      <span className="shrink-0 text-caption text-muted-foreground">
                        {formatDistanceToNow(new Date(meeting.scheduled_start), { addSuffix: true })}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
