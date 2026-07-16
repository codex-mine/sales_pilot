import { TrendingDown, TrendingUp, type IconComponent } from "@/icons";
import { cn } from "@/lib/utils";
import { Card } from "./card";
import { Skeleton } from "./skeleton";

export interface MetricCardProps {
  label: string;
  value: string | number;
  /** e.g. "+12.4%" — sign is inferred from `trend` for color/icon. */
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon?: IconComponent;
  isLoading?: boolean;
  className?: string;
}

const trendClass: Record<NonNullable<MetricCardProps["trend"]>, string> = {
  up: "text-success",
  down: "text-danger",
  neutral: "text-muted-foreground",
};

/** A single KPI tile: label, big value, optional trend delta and icon. The atomic unit of a MetricGrid. */
export function MetricCard({
  label,
  value,
  change,
  trend = "neutral",
  icon: Icon,
  isLoading = false,
  className,
}: MetricCardProps): React.ReactElement {
  if (isLoading) {
    return (
      <Card className={cn("flex flex-col gap-3", className)}>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-20" />
      </Card>
    );
  }

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : undefined;

  return (
    <Card className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center justify-between">
        <span className="text-body-sm font-medium text-muted-foreground">{label}</span>
        {Icon && (
          <span className="flex size-8 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Icon className="size-4" />
          </span>
        )}
      </div>
      <span className="text-heading-2 font-semibold tabular-nums text-foreground">{value}</span>
      {change && (
        <span className={cn("inline-flex items-center gap-1 text-body-sm font-medium", trendClass[trend])}>
          {TrendIcon && <TrendIcon className="size-3.5" />}
          {change}
        </span>
      )}
    </Card>
  );
}
