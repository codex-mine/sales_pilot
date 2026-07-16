import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface CenteredLayoutProps {
  children: ReactNode;
  maxWidthClassName?: string;
  className?: string;
}

/** Centers content both axes — auth forms, 404/error pages, onboarding steps. */
export function CenteredLayout({
  children,
  maxWidthClassName = "max-w-md",
  className,
}: CenteredLayoutProps): React.ReactElement {
  return (
    <div className={cn("flex min-h-screen w-full items-center justify-center p-4", className)}>
      <div className={cn("w-full", maxWidthClassName)}>{children}</div>
    </div>
  );
}
