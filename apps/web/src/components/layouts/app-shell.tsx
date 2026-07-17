"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Building2,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  User as UserIcon,
} from "@/icons";
import { Logo } from "@/components/brand/logo";
import { Avatar } from "@/components/ui/avatar";
import {
  Drawer,
  DrawerContent,
  DrawerTitle,
} from "@/components/ui/drawer";
import { VisuallyHidden } from "@/components/ui/visually-hidden";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";
import { AppLayout } from "@/components/layout/app-layout";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarNav,
  SidebarNavItem,
} from "@/components/ui/sidebar";
import { TopNav } from "@/components/ui/top-nav";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { getInitials } from "@/lib/utils";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/settings/organization", label: "Organization", icon: Building2 },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }): React.ReactElement {
  return (
    <SidebarNav>
      {navigation.map(({ href, label, icon }) => (
        <SidebarNavItem
          key={href}
          href={href}
          label={label}
          icon={icon}
          isActive={pathname === href}
          onClick={onNavigate}
        />
      ))}
    </SidebarNav>
  );
}

/** The authenticated app chrome: Sidebar (desktop) + slide-over nav (mobile) + TopNav, wired to the real signed-in user/organization. Render inside `<AuthGuard>`. */
export function AppShell({ children }: { children: ReactNode }): React.ReactElement {
  const pathname = usePathname();
  const router = useRouter();
  const { user, organization, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  async function handleLogout(): Promise<void> {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }

  return (
    <AppLayout
      sidebar={
        <Sidebar>
          <SidebarHeader>
            <Link href="/dashboard">
              <Logo size="sm" />
            </Link>
          </SidebarHeader>
          <SidebarContent>
            <NavLinks pathname={pathname} />
          </SidebarContent>
          <SidebarFooter>
            <p className="truncate px-1 text-caption text-sidebar-foreground/60">{organization?.name}</p>
          </SidebarFooter>
        </Sidebar>
      }
      topNav={
        <TopNav
          left={
            <>
              <IconButton
                icon={Menu}
                aria-label="Toggle navigation"
                variant="ghost"
                size="sm"
                className="lg:hidden"
                onClick={() => setMobileNavOpen(true)}
              />
              <span className="text-body-sm text-muted-foreground">{organization?.name}</span>
            </>
          }
          right={
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="flex items-center gap-2 rounded-md p-1 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Account menu"
                >
                  <Avatar size="sm" src={user?.avatar_url} fallback={user ? getInitials(user.full_name) : ""} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="truncate text-body-sm font-medium text-foreground">{user?.full_name}</p>
                  <p className="truncate text-caption font-normal text-muted-foreground">{user?.email}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings">
                    <UserIcon className="size-4" />
                    Profile settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="danger" onSelect={handleLogout} disabled={isLoggingOut}>
                  <LogOut className="size-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          }
        />
      }
    >
      <Drawer open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <DrawerContent side="left" className="w-72 max-w-[80vw] p-0">
          <VisuallyHidden>
            <DrawerTitle>Navigation</DrawerTitle>
          </VisuallyHidden>
          <div className="flex h-14 items-center border-b border-border px-4">
            <Link href="/dashboard">
              <Logo size="sm" />
            </Link>
          </div>
          <div className="p-3">
            <NavLinks pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </DrawerContent>
      </Drawer>

      <div className="p-4 md:p-8">{children}</div>
    </AppLayout>
  );
}
