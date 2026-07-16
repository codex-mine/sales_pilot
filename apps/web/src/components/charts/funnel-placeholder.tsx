import { Filter } from "@/icons";
import { cn } from "@/lib/utils";

export interface FunnelPlaceholderProps {
  height?: number;
  className?: string;
  label?: string;
}

/**
 * Reserves layout space and visual treatment for a future Funnel chart
 * (e.g. lead → opportunity → won conversion). See HeatmapPlaceholder for
 * why this ships as a placeholder rather than a real chart in this pass.
 */
export function FunnelPlaceholder({
  height = 320,
  className,
  label = "Funnel chart coming soon",
}: FunnelPlaceholderProps): React.ReactElement {
  return (
    <div
      style={{ height }}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/40 text-muted-foreground",
        className,
      )}
    >
      <Filter className="size-6" />
      <span className="text-body-sm">{label}</span>
    </div>
  );
}
