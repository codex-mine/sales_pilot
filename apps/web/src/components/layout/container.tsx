import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  /** Caps the max-width tier. `full` removes the cap entirely (still keeps side padding). */
  size?: "sm" | "md" | "lg" | "xl" | "full";
}

const sizeClass: Record<NonNullable<ContainerProps["size"]>, string> = {
  sm: "max-w-2xl",
  md: "max-w-4xl",
  lg: "max-w-6xl",
  xl: "max-w-7xl",
  full: "max-w-none",
};

/** Centers content with responsive horizontal padding and an optional max-width cap. The base layout primitive. */
export function Container({ size = "xl", className, ...props }: ContainerProps): React.ReactElement {
  return <div className={cn("mx-auto w-full px-4 sm:px-6 lg:px-8", sizeClass[size], className)} {...props} />;
}
