import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export const inputVariants = cva(
  [
    "flex w-full min-w-0 rounded-md border bg-card text-foreground",
    "text-body-md placeholder:text-muted-foreground",
    "transition-colors duration-fast ease-standard",
    "file:border-0 file:bg-transparent file:text-body-sm file:font-medium",
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
