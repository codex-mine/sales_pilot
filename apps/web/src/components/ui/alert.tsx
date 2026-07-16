import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type HTMLAttributes } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, type IconComponent } from "@/icons";
import { cn } from "@/lib/utils";

const alertVariants = cva("relative flex w-full gap-3 rounded-lg border p-4", {
  variants: {
    variant: {
      default: "border-border bg-card text-card-foreground",
      success: "border-transparent bg-success-soft text-success",
      warning: "border-transparent bg-warning-soft text-warning",
      danger: "border-transparent bg-danger-soft text-danger",
      info: "border-transparent bg-info-soft text-info",
    },
  },
  defaultVariants: { variant: "default" },
});

const defaultIcon: Record<NonNullable<VariantProps<typeof alertVariants>["variant"]>, IconComponent> = {
  default: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
  info: Info,
};

export interface AlertProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {
  icon?: IconComponent | null;
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", icon, children, ...props }, ref) => {
    const Icon = icon === null ? null : icon ?? defaultIcon[variant ?? "default"];

    return (
      <div ref={ref} role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
        {Icon && <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />}
        <div className="flex-1 text-body-sm [&_p]:leading-relaxed">{children}</div>
      </div>
    );
  },
);
Alert.displayName = "Alert";

export const AlertTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h5 ref={ref} className={cn("mb-1 text-body-md font-semibold leading-none", className)} {...props} />
  ),
);
AlertTitle.displayName = "AlertTitle";

export const AlertDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("text-body-sm opacity-90", className)} {...props} />
  ),
);
AlertDescription.displayName = "AlertDescription";
