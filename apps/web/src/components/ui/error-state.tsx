import { AlertTriangle } from "@/icons";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

/** A recoverable-error placeholder — for failed data fetches (distinct from EmptyState, which is not an error). */
export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  onRetry,
  retryLabel = "Retry",
  className,
}: ErrorStateProps): React.ReactElement {
  return (
    <div
      className={cn(
        "flex min-h-48 flex-col items-center justify-center gap-3 rounded-lg border border-border bg-danger-soft/40 p-8 text-center",
        className,
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-danger-soft text-danger">
        <AlertTriangle className="size-5" />
      </span>
      <div className="flex flex-col gap-1">
        <h3 className="text-body-lg font-medium text-foreground">{title}</h3>
        <p className="max-w-sm text-body-sm text-muted-foreground">{description}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-1">
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
