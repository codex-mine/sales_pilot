import { cn } from "@/lib/utils";
import { Spinner } from "./spinner";

export interface LoadingStateProps {
  label?: string;
  className?: string;
}

/** A centered spinner + label for a whole-panel loading state (prefer Skeleton for content-shaped loading). */
export function LoadingState({ label = "Loading...", className }: LoadingStateProps): React.ReactElement {
  return (
    <div className={cn("flex min-h-48 flex-col items-center justify-center gap-3", className)}>
      <Spinner size="lg" />
      <p className="text-body-sm text-muted-foreground">{label}</p>
    </div>
  );
}
