import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface TopNavProps {
  /** Left slot — typically a SidebarTrigger (mobile) + breadcrumb/workspace switcher. */
  left?: ReactNode;
  /** Center slot — typically a SearchInput. */
  center?: ReactNode;
  /** Right slot — typically notification bell, command palette trigger, user menu. */
  right?: ReactNode;
  className?: string;
}

/** The persistent top chrome bar — sits above page content, to the right of (or above, on mobile) the Sidebar. */
export function TopNav({ left, center, right, className }: TopNavProps): React.ReactElement {
  return (
    <header
      className={cn(
        // No hard border — the bar blends into the tinted canvas and only
        // reads as chrome via the blur when content scrolls beneath it.
        "sticky top-0 z-30 flex h-16 shrink-0 items-center gap-4 bg-background/80 px-4 backdrop-blur-sm sm:px-6 dark:border-b dark:border-border",
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-3">{left}</div>
      <div className="min-w-0 flex-1">{center}</div>
      <div className="flex items-center gap-2">{right}</div>
    </header>
  );
}
