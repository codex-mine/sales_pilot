import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export const inputVariants = cva(
  [
    "flex w-full min-w-0 rounded-lg border bg-muted text-foreground",
    "text-body-md placeholder:text-muted-foreground",
    "transition-all duration-fast ease-standard",
    "file:border-0 file:bg-transparent file:text-body-sm file:font-medium",
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
      size: {
        sm: "h-8 px-2.5 text-body-sm",
        md: "h-9 px-3",
        lg: "h-11 px-4 text-body-lg",
      },
    },
    defaultVariants: {
      state: "default",
      size: "md",
    },
  },
);

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  /** Wrapper element class name, when using leftIcon/rightIcon. */
  wrapperClassName?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, wrapperClassName, state, size, leftIcon, rightIcon, ...props }, ref) => {
    if (leftIcon || rightIcon) {
      return (
        <div className={cn("relative flex items-center", wrapperClassName)}>
          {leftIcon && (
            <span className="pointer-events-none absolute left-3 flex items-center text-muted-foreground [&_svg]:size-4">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            className={cn(
              inputVariants({ state, size }),
              leftIcon && "pl-9",
              rightIcon && "pr-9",
              className,
            )}
            {...props}
          />
          {rightIcon && (
            <span className="absolute right-3 flex items-center text-muted-foreground [&_svg]:size-4">
              {rightIcon}
            </span>
          )}
        </div>
      );
    }

    return <input ref={ref} className={cn(inputVariants({ state, size }), className)} {...props} />;
  },
);
Input.displayName = "Input";
