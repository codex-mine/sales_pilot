"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Building2, Shield, User } from "@/icons";
import { AuthGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { SidebarLayout } from "@/components/layout/sidebar-layout";
import { PageHeader } from "@/components/ui/page-header";
import { cn } from "@/lib/utils";

const settingsNav = [
  { href: "/settings", label: "Profile", icon: User },
  { href: "/settings/security", label: "Security", icon: Shield },
  { href: "/settings/organization", label: "Organization", icon: Building2 },
];

export default function SettingsLayout({ children }: { children: ReactNode }): React.ReactElement {
  const pathname = usePathname();

  return (
    <AuthGuard>
      <AppShell>
        <PageLayout>
          <PageHeader title="Settings" description="Manage your account, security, and workspace." />
          <SidebarLayout
            nav={
              <nav className="flex flex-col gap-1">
                {settingsNav.map(({ href, label, icon: Icon }) => {
                  const isActive = pathname === href;
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
        </PageLayout>
      </AppShell>
    </AuthGuard>
  );
}
