import type { Metadata } from "next";
import "@/styles/globals.css";
import { AppProviders } from "@/providers/app-providers";
export const metadata: Metadata = { title: "SalesPilot", description: "AI SDR platform" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>): React.ReactElement { return <html lang="en" suppressHydrationWarning><body><AppProviders>{children}</AppProviders></body></html>; }
