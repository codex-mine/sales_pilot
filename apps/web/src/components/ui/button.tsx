import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "@/icons";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  [
    "relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap",
    "rounded-lg text-body-md font-medium",
    "transition-all duration-fast ease-standard active:scale-[0.98]",
    "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100",
  ].join(" "),
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-sm hover:bg-primary-hover hover:shadow-md active:bg-primary-hover",
        secondary: "bg-secondary text-secondary-foreground hover:bg-muted",
        outline: "border border-border bg-transparent text-foreground hover:bg-muted hover:border-border",
        ghost: "bg-transparent text-foreground hover:bg-muted",
        soft: "bg-accent text-accent-foreground hover:bg-accent/70",
        success: "bg-success text-success-foreground shadow-sm hover:opacity-90 hover:shadow-md",
        warning: "bg-warning text-warning-foreground shadow-sm hover:opacity-90 hover:shadow-md",
        danger: "bg-danger text-danger-foreground shadow-sm hover:opacity-90 hover:shadow-md",
        link: "bg-transparent text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-body-sm",
        md: "h-9 px-4",
        lg: "h-11 px-6 text-body-lg",
        icon: "h-9 w-9 p-0",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render the child element instead of a `<button>` (e.g. wrap a Next.js `<Link>`). */
  asChild?: boolean;
  /** Shows a spinner in place of the leading content and disables interaction. */
  isLoading?: boolean;
  /** Text announced to screen readers while `isLoading` is true. Defaults to "Loading". */
  loadingText?: string;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      asChild = false,
      isLoading = false,
      loadingText = "Loading",
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        disabled={disabled ?? isLoading}
        aria-busy={isLoading || undefined}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            <span className="sr-only">{loadingText}</span>
            <span aria-hidden="true">{children}</span>
          </>
        ) : (
          children
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";
