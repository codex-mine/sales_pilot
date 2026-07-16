"use client";

import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

const avatarVariants = cva(
  "relative flex shrink-0 overflow-hidden rounded-full bg-muted text-muted-foreground",
  {
    variants: {
      size: {
        xs: "size-6 text-caption",
        sm: "size-8 text-body-sm",
        md: "size-10 text-body-md",
        lg: "size-12 text-body-lg",
        xl: "size-16 text-heading-5",
      },
    },
    defaultVariants: { size: "md" },
  },
);

export interface AvatarProps
  extends React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>,
    VariantProps<typeof avatarVariants> {
  src?: string | null;
  alt?: string;
  /** Fallback initials or icon shown while the image loads or is absent. */
  fallback?: React.ReactNode;
  /** Renders a small colored dot in the corner (online/offline/away/busy). */
  status?: "online" | "offline" | "away" | "busy";
}

const statusColor: Record<NonNullable<AvatarProps["status"]>, string> = {
  online: "bg-success",
  offline: "bg-muted-foreground",
  away: "bg-warning",
  busy: "bg-danger",
};

export const Avatar = forwardRef<React.ElementRef<typeof AvatarPrimitive.Root>, AvatarProps>(
  ({ className, size, src, alt = "", fallback, status, ...props }, ref) => (
    <span className="relative inline-flex">
      <AvatarPrimitive.Root ref={ref} className={cn(avatarVariants({ size }), className)} {...props}>
        {src && <AvatarPrimitive.Image src={src} alt={alt} className="aspect-square size-full object-cover" />}
        <AvatarPrimitive.Fallback
          className="flex size-full items-center justify-center font-medium"
          delayMs={src ? 400 : 0}
        >
          {fallback}
        </AvatarPrimitive.Fallback>
      </AvatarPrimitive.Root>
      {status && (
        <span
          className={cn(
            "absolute bottom-0 right-0 size-2.5 rounded-full ring-2 ring-background",
            statusColor[status],
          )}
          aria-hidden="true"
        />
      )}
    </span>
  ),
);
Avatar.displayName = "Avatar";
