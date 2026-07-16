import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "@/icons";
import { cn } from "@/lib/utils";

const spinnerVariants = cva("animate-spin text-current", {
  variants: {
    size: {
      sm: "size-4",
      md: "size-5",
      lg: "size-7",
    },
  },
  defaultVariants: { size: "md" },
});

export interface SpinnerProps extends VariantProps<typeof spinnerVariants> {
  className?: string;
  /** Accessible label for screen readers (visually hidden). Defaults to "Loading". */
  label?: string;
}

export function Spinner({ size, className, label = "Loading" }: SpinnerProps): React.ReactElement {
  return (
    <span role="status" className="inline-flex">
      <Loader2 className={cn(spinnerVariants({ size }), className)} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  );
}
