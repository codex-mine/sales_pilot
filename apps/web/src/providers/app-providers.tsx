"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
export function AppProviders({ children }: { children: ReactNode }): React.ReactElement {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } }));
  return <ThemeProvider attribute="class" defaultTheme="system" enableSystem><QueryClientProvider client={client}>{children}</QueryClientProvider></ThemeProvider>;
}
