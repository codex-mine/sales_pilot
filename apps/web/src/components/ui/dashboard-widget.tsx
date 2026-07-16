import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Card } from "./card";
import { ErrorState } from "./error-state";
import { LoadingState } from "./loading-state";

export interface DashboardWidgetProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  className?: string;
}

/** The standard dashboard grid tile: title/description/actions header + a content area with built-in loading/error states. */
export function DashboardWidget({
  title,
  description,
  actions,
  children,
  isLoading = false,
  error,
  onRetry,
  className,
}: DashboardWidgetProps): React.ReactElement {
  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-start justify-between gap-4 pb-4">
        <div className="flex flex-col gap-0.5">
          <h3 className="text-body-md font-semibold text-foreground">{title}</h3>
          {description && <p className="text-body-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className="flex-1">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState description={error} onRetry={onRetry} />
        ) : (
          children
        )}
      </div>
    </Card>
  );
}
