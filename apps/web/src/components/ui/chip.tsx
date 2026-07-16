import { forwardRef, type HTMLAttributes } from "react";
import { X } from "@/icons";
import { cn } from "@/lib/utils";

export interface ChipProps extends HTMLAttributes<HTMLDivElement> {
  /** Renders a trailing remove (×) affordance. */
  onRemove?: () => void;
  removeLabel?: string;
  disabled?: boolean;
}

/** A removable tag/filter pill — distinct from Badge (status) in that it represents a user-controlled selection. */
export const Chip = forwardRef<HTMLDivElement, ChipProps>(
  ({ className, children, onRemove, removeLabel = "Remove", disabled, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "inline-flex h-7 items-center gap-1 rounded-md border border-border bg-secondary pl-2.5 pr-1.5 text-body-sm text-secondary-foreground",
        disabled && "opacity-50",
        className,
      )}
      {...props}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="rounded-sm p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={removeLabel}
        >
          <X className="size-3" />
        </button>
      )}
    </div>
  ),
);
Chip.displayName = "Chip";
