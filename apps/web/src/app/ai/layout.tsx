"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Bot, FileText, History, Settings as SettingsIcon } from "@/icons";
import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { SidebarLayout } from "@/components/layout/sidebar-layout";
import { PageHeader } from "@/components/ui/page-header";
import { cn } from "@/lib/utils";

const aiNav = [
  { href: "/ai", label: "Job history", icon: History },
  { href: "/ai/agents", label: "Agents", icon: Bot },
  { href: "/ai/prompts", label: "Prompts", icon: FileText },
  { href: "/ai/settings", label: "Settings", icon: SettingsIcon },
];

export default function AILayout({ children }: { children: ReactNode }): React.ReactElement {
  const pathname = usePathname();

  return (
    <AuthGuard>
      <AppShell>
        <PageLayout>
          <PageHeader
            title="AI"
            description="Every AI call the system makes — providers, agents, prompts, jobs, and spend — in one place."
          />
          <PermissionGuard permission="ai.read" redirectTo="/dashboard">
            <SidebarLayout
              nav={
                <nav className="flex flex-col gap-1">
                  {aiNav.map(({ href, label, icon: Icon }) => {
                    const isActive = href === "/ai" ? pathname === href : pathname.startsWith(href);
                    return (
                      <Link
                        key={href}
                        href={href}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-3 py-2 text-body-sm font-medium transition-colors",
                          isActive
                            ? "bg-accent text-accent-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground",
                        )}
                      >
                        <Icon className="size-4" />
                        {label}
                      </Link>
                    );
                  })}
                </nav>
              }
            >
              {children}
            </SidebarLayout>
          </PermissionGuard>
        </PageLayout>
      </AppShell>
    </AuthGuard>
  );
}
