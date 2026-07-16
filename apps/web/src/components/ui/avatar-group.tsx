import { Children, isValidElement, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Avatar } from "./avatar";

export interface AvatarGroupProps {
  children: ReactNode;
  /** Caps visible avatars, collapsing the rest into a "+N" badge. */
  max?: number;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
}

/** Overlapping stack of avatars, e.g. "assigned to" or "participants" summaries. */
export function AvatarGroup({ children, max, size = "md", className }: AvatarGroupProps): React.ReactElement {
  const items = Children.toArray(children).filter(isValidElement);
  const visible = max ? items.slice(0, max) : items;
  const overflow = max ? items.length - max : 0;

  return (
    <div className={cn("flex items-center -space-x-2", className)}>
      {visible.map((child, index) => (
        <span key={index} className="ring-2 ring-background rounded-full">
          {child}
        </span>
      ))}
      {overflow > 0 && (
        <Avatar
          size={size}
          fallback={`+${overflow}`}
          className="ring-2 ring-background"
        />
      )}
    </div>
  );
}
