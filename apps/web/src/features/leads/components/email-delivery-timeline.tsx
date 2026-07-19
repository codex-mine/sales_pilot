"use client";

import { formatDistanceToNow } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import { Timeline, TimelineItem } from "@/components/ui/timeline";
import {
  AlertTriangle,
  CheckCircle2,
  Mail,
  MailX,
  MousePointerClick,
  Send,
  XCircle,
} from "@/icons";
import { useEmailTimeline } from "../hooks/use-lead-tracking";
import type { EmailEventResponse } from "../types";

export interface EmailDeliveryTimelineProps {
  emailId: string;
}

const EVENT_META: Record<
  string,
  { label: string; icon: typeof Send; tone: "default" | "success" | "warning" | "danger" | "info" | "primary" }
> = {
  queued: { label: "Queued", icon: Send, tone: "default" },
  sent: { label: "Sent", icon: Send, tone: "primary" },
  delivered: { label: "Delivered", icon: CheckCircle2, tone: "info" },
  opened: { label: "Opened", icon: Mail, tone: "success" },
  clicked: { label: "Clicked", icon: MousePointerClick, tone: "success" },
  bounced: { label: "Bounced", icon: XCircle, tone: "danger" },
  complained: { label: "Marked as spam", icon: AlertTriangle, tone: "danger" },
  failed: { label: "Failed", icon: XCircle, tone: "danger" },
  unsubscribed: { label: "Unsubscribed", icon: MailX, tone: "warning" },
};

function eventTitle(event: EmailEventResponse): string {
  const meta = EVENT_META[event.event_type];
  const label = meta?.label ?? event.event_type;
  if (event.metadata?.likely_bot) return `${label} (likely automated, not counted)`;
  return label;
}

/** Vertical delivery/engagement timeline for one sent email — reuses the
 * same Timeline component the Company Research panel uses for its "Recent
 * News" list, not a bespoke stepper. */
export function EmailDeliveryTimeline({ emailId }: EmailDeliveryTimelineProps): React.ReactElement | null {
  const { timeline, isLoading } = useEmailTimeline(emailId);

  if (isLoading) {
    return <Skeleton className="h-24 w-full" />;
  }
  if (!timeline || timeline.events.length === 0) {
    return null;
  }

  return (
    <Timeline>
      {timeline.events.map((event, index) => {
        const meta = EVENT_META[event.event_type];
        return (
          <TimelineItem
            key={event.id}
            icon={meta?.icon ?? Send}
            tone={event.metadata?.likely_bot ? "default" : meta?.tone ?? "default"}
            title={eventTitle(event)}
            description={event.bounce_reason ?? event.click_url ?? undefined}
            timestamp={formatDistanceToNow(new Date(event.occurred_at), { addSuffix: true })}
            isLast={index === timeline.events.length - 1}
          />
        );
      })}
    </Timeline>
  );
}
