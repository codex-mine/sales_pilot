import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface SidebarLayoutProps {
  /** A secondary, in-page navigation column (e.g. Settings sub-nav) — not the app's primary Sidebar. */
  nav: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Two-column layout: a fixed-width nav rail beside flexible content. Stacks vertically below `lg`. */
export function SidebarLayout({ nav, children, className }: SidebarLayoutProps): React.ReactElement {
  return (
    <div className={cn("flex flex-col gap-8 lg:flex-row", className)}>
      <aside className="shrink-0 lg:w-56">{nav}</aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
