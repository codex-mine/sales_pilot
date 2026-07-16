import type { ReactNode } from "react";
import type { IconComponent } from "@/icons";
import { cn } from "@/lib/utils";

export function Timeline({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("flex flex-col", className)}>{children}</div>;
}

export interface TimelineItemProps {
  icon?: IconComponent;
  title: ReactNode;
  description?: ReactNode;
  timestamp?: ReactNode;
  /** Hides the connecting line below this item — set on the last item. */
  isLast?: boolean;
  tone?: "default" | "success" | "warning" | "danger" | "info" | "primary";
}

const toneClass: Record<NonNullable<TimelineItemProps["tone"]>, string> = {
  default: "bg-muted text-muted-foreground",
  primary: "bg-accent text-accent-foreground",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
};

export function TimelineItem({
  icon: Icon,
  title,
  description,
  timestamp,
  isLast = false,
  tone = "default",
}: TimelineItemProps): React.ReactElement {
  return (
    <div className="relative flex gap-3 pb-6 last:pb-0">
      {!isLast && <span className="absolute left-3.5 top-8 h-[calc(100%-1.5rem)] w-px bg-border" aria-hidden="true" />}
      <span
        className={cn(
          "z-10 flex size-7 shrink-0 items-center justify-center rounded-full",
          toneClass[tone],
        )}
      >
        {Icon && <Icon className="size-3.5" />}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 pt-0.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-body-sm font-medium text-foreground">{title}</span>
          {timestamp && <span className="shrink-0 text-caption text-muted-foreground">{timestamp}</span>}
        </div>
        {description && <p className="text-body-sm text-muted-foreground">{description}</p>}
      </div>
    </div>
  );
}
