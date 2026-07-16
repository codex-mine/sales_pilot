import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Avatar } from "./avatar";

export interface ActivityItemProps {
  actorName: string;
  actorAvatarSrc?: string;
  /** e.g. "changed the status to" — rendered between the actor and the target. */
  action: ReactNode;
  target?: ReactNode;
  timestamp: string;
  className?: string;
}

/** A single audit/activity-log row: "{Actor} {action} {target}" plus a timestamp — pairs with Timeline for full feeds. */
export function ActivityItem({
  actorName,
  actorAvatarSrc,
  action,
  target,
  timestamp,
  className,
}: ActivityItemProps): React.ReactElement {
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <Avatar size="sm" src={actorAvatarSrc} fallback={actorName.slice(0, 2).toUpperCase()} />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="text-body-sm text-foreground">
          <span className="font-medium">{actorName}</span> <span className="text-muted-foreground">{action}</span>{" "}
          {target && <span className="font-medium">{target}</span>}
        </p>
        <span className="text-caption text-muted-foreground">{timestamp}</span>
      </div>
    </div>
  );
}
