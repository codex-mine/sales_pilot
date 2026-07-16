"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

/**
 * App-wide toast host. Mount once near the root (see `app/layout.tsx`);
 * trigger toasts anywhere via `import { toast } from "sonner"`.
 * Styling is fully token-driven through CSS variables passed as inline
 * style properties — Sonner has no notion of our Tailwind theme otherwise.
 */
export function Toaster({ ...props }: ToasterProps): React.ReactElement {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-popover group-[.toaster]:text-popover-foreground group-[.toaster]:border-border group-[.toaster]:shadow-floating group-[.toaster]:rounded-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          success: "group-[.toast]:text-success",
          error: "group-[.toast]:text-danger",
          warning: "group-[.toast]:text-warning",
          info: "group-[.toast]:text-info",
        },
      }}
      {...props}
    />
  );
}
