import type { ReactNode } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

export interface AppLayoutProps {
  /** Typically a composed <Sidebar>...</Sidebar> tree. */
  sidebar: ReactNode;
  /** Typically a <TopNav /> instance. */
  topNav?: ReactNode;
  children: ReactNode;
  defaultSidebarCollapsed?: boolean;
  className?: string;
}

/**
 * The authenticated-app shell: collapsible Sidebar + sticky TopNav + a
 * scrollable main content column. This owns chrome only — page content
 * (dashboards, tables, forms) is always the `children` passed in.
 */
export function AppLayout({
  sidebar,
  topNav,
  children,
  defaultSidebarCollapsed = false,
  className,
}: AppLayoutProps): React.ReactElement {
  return (
    <SidebarProvider defaultCollapsed={defaultSidebarCollapsed}>
      {sidebar}
      <div className={cn("flex min-w-0 flex-1 flex-col", className)}>
        {topNav}
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </SidebarProvider>
  );
}
