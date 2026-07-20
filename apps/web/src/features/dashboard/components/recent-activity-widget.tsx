"use client";

import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { History } from "@/icons";
import type { RecentActivityItem } from "../types";

export interface RecentActivityWidgetProps {
  activity: RecentActivityItem[] | undefined;
  isLoading: boolean;
}

/** Org-wide feed — every module's `Activity.summary` is already a
 * human-readable sentence set at record time, so this renders it directly
 * rather than re-deriving per-type labels the way the per-lead timeline
 * does (that map only covers lead-scoped types; this feed spans all of
 * them, across every module). */
export function RecentActivityWidget({ activity, isLoading }: RecentActivityWidgetProps): React.ReactElement {
  const items = activity ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="size-4" />
          Recent Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-body-sm text-muted-foreground">No activity yet.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {items.map((item) => (
              <div key={item.id} className="flex items-start gap-2.5">
                <History className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                <div className="flex min-w-0 flex-col">
                  <p className="text-body-sm text-foreground">
                    {item.actor_name && <span className="font-medium">{item.actor_name} </span>}
                    {item.summary ?? item.activity_type.replaceAll("_", " ")}
                  </p>
                  <span className="text-caption text-muted-foreground">
                    {formatDistanceToNow(new Date(item.occurred_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
