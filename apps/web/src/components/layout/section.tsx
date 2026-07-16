import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface SectionProps extends HTMLAttributes<HTMLElement> {
  /** Adds a top divider — use when stacking multiple Sections in one page. */
  divider?: boolean;
  spacing?: "sm" | "md" | "lg";
}

const spacingClass: Record<NonNullable<SectionProps["spacing"]>, string> = {
  sm: "py-4",
  md: "py-8",
  lg: "py-12",
};

/** Vertical rhythm wrapper for a distinct page section — consistent spacing instead of ad-hoc margins. */
export function Section({ divider = false, spacing = "md", className, ...props }: SectionProps): React.ReactElement {
  return (
    <section
      className={cn(spacingClass[spacing], divider && "border-t border-border", className)}
      {...props}
    />
  );
}
