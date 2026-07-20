"use client";

import { IconButton } from "@/components/ui/icon-button";
import { X } from "@/icons";

export interface DashboardWidgetFrameProps {
  onRemove?: () => void;
  children: React.ReactNode;
}

/** Thin positioning wrapper that overlays a remove button on top of a
 * widget's own Card — avoids touching each widget component's own header. */
export function DashboardWidgetFrame({ onRemove, children }: DashboardWidgetFrameProps): React.ReactElement {
  return (
    <div className="group relative">
      {onRemove && (
        <IconButton
          icon={X}
          variant="ghost"
          size="sm"
          aria-label="Remove widget"
          className="absolute right-2 top-2 z-10 opacity-0 transition-opacity group-hover:opacity-100"
          onClick={onRemove}
        />
      )}
      {children}
    </div>
  );
}
