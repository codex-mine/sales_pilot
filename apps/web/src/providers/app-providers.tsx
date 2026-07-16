"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuthStore } from "@/store/auth-store";

/** Runs the auth boot sequence exactly once, on mount, before anything gated by `<AuthGuard>`/`<GuestGuard>` can render. */
function AuthInitializer(): null {
  const initialize = useAuthStore((state) => state.initialize);
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    void initialize();
  }, [initialize]);

  return null;
}

export function AppProviders({ children }: { children: ReactNode }): React.ReactElement {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } }),
  );
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={client}>
        <TooltipProvider delayDuration={200}>
          <AuthInitializer />
          {children}
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
