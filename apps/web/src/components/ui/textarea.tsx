import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const textareaVariants = cva(
  [
    "flex w-full rounded-md border bg-card px-3 py-2 text-foreground",
    "text-body-md placeholder:text-muted-foreground",
    "transition-colors duration-fast ease-standard",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:opacity-70",
  ].join(" "),
  {
    variants: {
      state: {
        default: "border-input focus-visible:ring-ring",
        success: "border-success focus-visible:ring-success",
        error: "border-danger focus-visible:ring-danger",
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
