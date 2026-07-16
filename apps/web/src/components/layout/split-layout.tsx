import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface SplitLayoutProps {
  /** e.g. a record list. Fixed width on desktop. */
  primary: ReactNode;
  /** e.g. a record detail panel. Fills remaining space; hidden on mobile unless `secondary` is the active view. */
  secondary: ReactNode;
  primaryWidthClassName?: string;
  className?: string;
}

/** A two-pane master/detail layout (list + detail view) — e.g. an inbox or a leads list with a preview panel. */
export function SplitLayout({
  primary,
  secondary,
  primaryWidthClassName = "lg:w-96",
  className,
}: SplitLayoutProps): React.ReactElement {
  return (
    <div className={cn("flex h-full min-h-0 flex-1 flex-col lg:flex-row", className)}>
      <div className={cn("flex min-h-0 shrink-0 flex-col border-border lg:border-r", primaryWidthClassName)}>
        {primary}
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">{secondary}</div>
    </div>
  );
}
