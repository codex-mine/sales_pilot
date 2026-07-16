import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface EmptyLayoutProps {
  children: ReactNode;
  className?: string;
}

/** Bare page shell with no sidebar/nav chrome — auth screens (login, register, reset password). */
export function EmptyLayout({ children, className }: EmptyLayoutProps): React.ReactElement {
  return <div className={cn("min-h-screen bg-background", className)}>{children}</div>;
}
