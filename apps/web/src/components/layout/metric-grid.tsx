import type { HTMLAttributes } from "react";
import { ResponsiveGrid } from "./responsive-grid";

export interface MetricGridProps extends HTMLAttributes<HTMLDivElement> {
  columns?: 2 | 3 | 4;
}

/** A ResponsiveGrid preset sized for MetricCard/StatCard rows — 1 col on mobile up to `columns` on desktop. */
export function MetricGrid({ columns = 4, className, ...props }: MetricGridProps): React.ReactElement {
  return (
    <ResponsiveGrid
      cols={{ base: 1, sm: 2, lg: columns }}
      gap="md"
      className={className}
      {...props}
    />
  );
}
