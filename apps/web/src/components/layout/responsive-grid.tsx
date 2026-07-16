import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface ResponsiveGridProps extends HTMLAttributes<HTMLDivElement> {
  /** Column count at each breakpoint. Omit a key to inherit the previous breakpoint's value. */
  cols?: { base?: number; sm?: number; md?: number; lg?: number; xl?: number };
  gap?: "sm" | "md" | "lg";
}

const colsClassMap: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
  5: "grid-cols-5",
  6: "grid-cols-6",
  12: "grid-cols-12",
};

const smColsClassMap: Record<number, string> = {
  1: "sm:grid-cols-1",
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-3",
  4: "sm:grid-cols-4",
  6: "sm:grid-cols-6",
};

const mdColsClassMap: Record<number, string> = {
  1: "md:grid-cols-1",
  2: "md:grid-cols-2",
  3: "md:grid-cols-3",
  4: "md:grid-cols-4",
  6: "md:grid-cols-6",
};

const lgColsClassMap: Record<number, string> = {
  1: "lg:grid-cols-1",
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
  6: "lg:grid-cols-6",
  12: "lg:grid-cols-12",
};

const xlColsClassMap: Record<number, string> = {
  1: "xl:grid-cols-1",
  2: "xl:grid-cols-2",
  3: "xl:grid-cols-3",
  4: "xl:grid-cols-4",
  6: "xl:grid-cols-6",
  12: "xl:grid-cols-12",
};

const gapClass: Record<NonNullable<ResponsiveGridProps["gap"]>, string> = {
  sm: "gap-3",
  md: "gap-6",
  lg: "gap-8",
};

/**
 * A CSS grid with per-breakpoint column counts — the design system's answer
 * to "adapt layouts, don't just shrink components." Defaults to a 1 → 2 → 4
 * column progression, the common metric-grid/card-grid pattern.
 */
export function ResponsiveGrid({
  cols = { base: 1, sm: 2, lg: 4 },
  gap = "md",
  className,
  ...props
}: ResponsiveGridProps): React.ReactElement {
  return (
    <div
      className={cn(
        "grid",
        cols.base && colsClassMap[cols.base],
        cols.sm && smColsClassMap[cols.sm],
        cols.md && mdColsClassMap[cols.md],
        cols.lg && lgColsClassMap[cols.lg],
        cols.xl && xlColsClassMap[cols.xl],
        gapClass[gap],
        className,
      )}
      {...props}
    />
  );
}
