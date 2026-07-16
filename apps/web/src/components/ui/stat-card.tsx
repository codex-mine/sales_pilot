import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Card } from "./card";
import { CircularProgress } from "./circular-progress";
import { Skeleton } from "./skeleton";

export interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  /** 0-100 — renders a circular progress ring alongside the value (e.g. quota attainment). */
  progress?: number;
  isLoading?: boolean;
  footer?: ReactNode;
  className?: string;
}

/** A card pairing a headline stat with supporting context and an optional progress ring — for goals/quotas/capacity. */
export function StatCard({
  title,
  value,
  description,
  progress,
  isLoading = false,
  footer,
  className,
}: StatCardProps): React.ReactElement {
  if (isLoading) {
    return (
      <Card className={cn("flex flex-col gap-4", className)}>
        <Skeleton className="h-4 w-28" />
        <div className="flex items-center gap-4">
          <Skeleton className="size-12 rounded-full" />
          <Skeleton className="h-8 w-20" />
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn("flex flex-col gap-4", className)}>
      <div className="flex items-center justify-between">
        <span className="text-body-sm font-medium text-muted-foreground">{title}</span>
      </div>
      <div className="flex items-center gap-4">
        {progress !== undefined && <CircularProgress value={progress} size={56} />}
        <div className="flex flex-col">
          <span className="text-heading-2 font-semibold tabular-nums text-foreground">{value}</span>
          {description && <span className="text-body-sm text-muted-foreground">{description}</span>}
        </div>
      </div>
      {footer && <div className="border-t border-border pt-3">{footer}</div>}
    </Card>
  );
}
