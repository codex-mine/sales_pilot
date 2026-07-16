import { LayoutGrid } from "@/icons";
import { cn } from "@/lib/utils";

export interface HeatmapPlaceholderProps {
  height?: number;
  className?: string;
  label?: string;
}

/**
 * Reserves layout space and visual treatment for a future Heatmap chart
 * (e.g. send-time-vs-open-rate). Intentionally not a real chart yet — swap
 * for a real implementation without changing how callers size/place it.
 */
export function HeatmapPlaceholder({
  height = 320,
  className,
  label = "Heatmap coming soon",
}: HeatmapPlaceholderProps): React.ReactElement {
  return (
    <div
      style={{ height }}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/40 text-muted-foreground",
        className,
      )}
    >
      <LayoutGrid className="size-6" />
      <span className="text-body-sm">{label}</span>
    </div>
  );
}
