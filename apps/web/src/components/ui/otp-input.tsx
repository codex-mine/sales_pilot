"use client";

import { OTPInput, OTPInputContext } from "input-otp";
import { forwardRef, useContext } from "react";
import { cn } from "@/lib/utils";

export const OtpInput = forwardRef<React.ElementRef<typeof OTPInput>, React.ComponentPropsWithoutRef<typeof OTPInput>>(
  ({ className, containerClassName, ...props }, ref) => (
    <OTPInput
      ref={ref}
      containerClassName={cn("flex items-center gap-2 has-[:disabled]:opacity-50", containerClassName)}
      className={cn("disabled:cursor-not-allowed", className)}
      {...props}
    />
  ),
);
OtpInput.displayName = "OtpInput";

export function OtpInputGroup({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): React.ReactElement {
  return <div className={cn("flex items-center gap-2", className)} {...props} />;
}

export function OtpInputSlot({ index, className }: { index: number; className?: string }): React.ReactElement {
  const inputOTPContext = useContext(OTPInputContext);
  const slot = inputOTPContext.slots[index];
  if (!slot) throw new Error(`OtpInputSlot: no slot at index ${index}`);
  const { char, hasFakeCaret, isActive } = slot;

  return (
    <div
      className={cn(
        "relative flex size-10 items-center justify-center rounded-md border border-input bg-card text-body-lg font-medium text-foreground",
        "transition-colors duration-fast ease-standard",
        isActive && "z-10 ring-2 ring-ring ring-offset-2 ring-offset-background",
        className,
      )}
    >
      {char}
      {hasFakeCaret && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-4 w-px animate-pulse bg-foreground" />
        </div>
      )}
    </div>
  );
}

export function OtpInputSeparator(): React.ReactElement {
  return <span className="text-muted-foreground">–</span>;
}
