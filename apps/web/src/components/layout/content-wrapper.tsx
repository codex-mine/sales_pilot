import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** Bare padding wrapper — for panels/drawers/modals that need consistent inset without Container's max-width/centering. */
export function ContentWrapper({ className, ...props }: HTMLAttributes<HTMLDivElement>): React.ReactElement {
  return <div className={cn("p-4 sm:p-6", className)} {...props} />;
}
