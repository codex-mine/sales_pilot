"use client";

import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "@/icons";
import { cn } from "@/lib/utils";
import { Input, type InputProps } from "./input";

export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputProps, "type" | "rightIcon">>(
  ({ className, ...props }, ref) => {
    const [visible, setVisible] = useState(false);

    return (
      <Input
        ref={ref}
        type={visible ? "text" : "password"}
        autoComplete="current-password"
        className={cn("pr-9", className)}
        rightIcon={
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setVisible((prev) => !prev)}
            className="pointer-events-auto rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={visible ? "Hide password" : "Show password"}
          >
            {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        }
        {...props}
      />
    );
  },
);
PasswordInput.displayName = "PasswordInput";
