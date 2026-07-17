import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const textareaVariants = cva(
  [
    "flex w-full rounded-lg border bg-muted px-3 py-2 text-foreground",
    "text-body-md placeholder:text-muted-foreground",
    "transition-all duration-fast ease-standard",
    "hover:bg-muted/70",
    "focus-visible:!outline-none focus-visible:bg-card focus-visible:ring-4",
    "disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:opacity-70 disabled:hover:bg-muted",
  ].join(" "),
  {
    variants: {
      state: {
        default: "border-transparent focus-visible:border-ring focus-visible:ring-ring/10",
        success: "border-success bg-card hover:bg-card focus-visible:border-success focus-visible:ring-success/10",
        error: "border-danger bg-card hover:bg-card focus-visible:border-danger focus-visible:ring-danger/10",
      },
    },
    defaultVariants: {
      state: "default",
    },
  },
);

export interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  /** Shows a live `n / max` character counter beneath the field (requires `maxLength`). */
  showCharacterCount?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, state, showCharacterCount, maxLength, value, defaultValue, ...props }, ref) => {
    const length = typeof value === "string" ? value.length : undefined;

    return (
      <div className="w-full">
        <textarea
          ref={ref}
          className={cn(textareaVariants({ state }), "min-h-24 resize-y", className)}
          maxLength={maxLength}
          value={value}
          defaultValue={defaultValue}
          {...props}
        />
        {showCharacterCount && maxLength !== undefined && (
          <div className="mt-1 text-right text-caption text-muted-foreground">
            {length ?? 0} / {maxLength}
          </div>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";
