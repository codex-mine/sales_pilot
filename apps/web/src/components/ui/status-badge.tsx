import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const dotVariants = cva("size-1.5 rounded-full", {
  variants: {
    tone: {
      neutral: "bg-muted-foreground",
      success: "bg-success",
      warning: "bg-warning",
      danger: "bg-danger",
      info: "bg-info",
      primary: "bg-primary",
    },
  },
  defaultVariants: { tone: "neutral" },
});

const wrapperVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 h-6 text-caption font-medium leading-none",
  {
    variants: {
      tone: {
        neutral: "border-border bg-secondary text-secondary-foreground",
        success: "border-transparent bg-success-soft text-success",
        warning: "border-transparent bg-warning-soft text-warning",
        danger: "border-transparent bg-danger-soft text-danger",
        info: "border-transparent bg-info-soft text-info",
        primary: "border-transparent bg-accent text-accent-foreground",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface StatusBadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof wrapperVariants> {
  /** Adds a subtle pulse to the dot — use for "live"/in-progress states only. */
  pulse?: boolean;
}

/** A labeled status pill with a leading dot — for record states (Active, Draft, Failed, ...). */
export function StatusBadge({
  className,
  tone,
  pulse = false,
  children,
  ...props
}: StatusBadgeProps): React.ReactElement {
  return (
    <span className={cn(wrapperVariants({ tone }), className)} {...props}>
      <span className="relative flex size-1.5">
        {pulse && (
          <span
            className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-75", dotVariants({ tone }))}
          />
        )}
        <span className={cn("relative inline-flex", dotVariants({ tone }))} />
      </span>
      {children}
    </span>
  );
}
