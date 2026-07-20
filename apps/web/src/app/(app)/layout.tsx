import type { ReactNode } from "react";
import { AuthGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";

/**
 * Shared chrome for every authenticated route (dashboard, leads, companies,
 * inbox, meetings, settings, ai, ...). A Next.js layout persists across
 * client-side navigation between routes under the same layout — unlike a
 * per-page `<AuthGuard><AppShell>` wrapper, which would fully unmount and
 * remount the Sidebar (and its collapse/expand state) on every navigation,
 * producing a visible "sidebar shrinks then snaps back" flicker. Mounting
 * AppShell here once means the Sidebar/TopNav never remount when moving
 * between pages in this group — only `children` swaps.
 */
export default function AppRouteGroupLayout({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
