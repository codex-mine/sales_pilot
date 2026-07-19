"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Bell,
  Bot,
  Briefcase,
  Building2,
  FileText,
  History,
  Inbox,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  MessagesSquare,
  Settings,
  Settings2,
  Shield,
  User as UserIcon,
  Users,
  type IconComponent,
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
  SidebarNavCollapsible,
  SidebarNavItem,
} from "@/components/ui/sidebar";
import { TopNav } from "@/components/ui/top-nav";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { useConversations } from "@/features/inbox/hooks/use-conversations";
import { getInitials } from "@/lib/utils";

type NavEntry =
  | { href: string; label: string; icon: IconComponent }
  | { label: string; icon: IconComponent; items: { href: string; label: string; icon: IconComponent }[] };

const navigation: NavEntry[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/companies", label: "Companies", icon: Briefcase },
  { href: "/email-templates", label: "Email Templates", icon: Mail },
  { href: "/outreach/outbox", label: "Outbox", icon: Inbox },
  { href: "/inbox", label: "Inbox", icon: MessagesSquare },
  {
    label: "AI",
    icon: Bot,
    items: [
      { href: "/ai", label: "Job History", icon: History },
      { href: "/ai/agents", label: "Agents", icon: Bot },
      { href: "/ai/prompts", label: "Prompts", icon: FileText },
      { href: "/ai/settings", label: "Settings", icon: Settings2 },
    ],
  },
  {
    label: "Settings",
    icon: Settings,
    items: [
      { href: "/settings", label: "Profile", icon: UserIcon },
      { href: "/settings/security", label: "Security", icon: Shield },
      { href: "/settings/organization", label: "Organization", icon: Building2 },
    ],
  },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }): React.ReactElement {
  return (
    <SidebarNav>
      {navigation.map((entry) => {
        if ("items" in entry) {
          const items = entry.items.map((item) => ({ ...item, isActive: pathname === item.href }));
          return (
            <SidebarNavCollapsible
              key={entry.label}
              icon={entry.icon}
              label={entry.label}
              items={items}
              isActiveGroup={items.some((item) => item.isActive)}
              onNavigate={onNavigate}
            />
          );
        }
        return (
          <SidebarNavItem
            key={entry.href}
            href={entry.href}
            label={entry.label}
            icon={entry.icon}
            // "Leads" and "Companies" have sub-routes (/leads/[id],
            // /leads/import, /companies/[id], ...) without their own nav
            // entries, so they need prefix matching to stay highlighted
            // there; every other item maps 1:1 to a literal href.
            isActive={
              entry.href === "/leads" || entry.href === "/companies"
                ? pathname.startsWith(entry.href)
                : pathname === entry.href
            }
            onClick={onNavigate}
          />
        );
      })}
    </SidebarNav>
  );
}

const HEADER_ICON_BUTTON_CLASS =
  "relative flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-ring";

function UnreadCountBadge({ count }: { count: number }): React.ReactElement | null {
  if (count <= 0) return null;
  return (
    <span
      className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-danger-foreground"
      aria-hidden="true"
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

/** Messages quick-icon — links straight to the Inbox and surfaces the real unread-conversation count
 * (reuses the existing Inbox list query, just with `page_size: 1` since only `meta.total` is needed here). */
function MessagesQuickLink(): React.ReactElement {
  const { meta } = useConversations({ unread_only: true, page: 1, page_size: 1 });

  return (
    <Link
      href="/inbox"
      aria-label={meta.total > 0 ? `Messages — ${meta.total} unread` : "Messages"}
      className={HEADER_ICON_BUTTON_CLASS}
    >
      <MessagesSquare className="size-4" />
      <UnreadCountBadge count={meta.total} />
    </Link>
  );
}

/** Notification bell — placeholder only for now; no notification feed exists yet. */
function NotificationsQuickMenu(): React.ReactElement {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className={HEADER_ICON_BUTTON_CLASS} aria-label="Notifications">
          <Bell className="size-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
          <Bell className="size-6 text-muted-foreground" />
          <p className="text-body-sm text-muted-foreground">Notifications are coming soon.</p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
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
              <Logo size="md" />
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
            <div className="flex items-center gap-1">
              <MessagesQuickLink />
              <NotificationsQuickMenu />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    className="flex items-center gap-2 rounded-md p-1 transition-colors hover:bg-muted focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
            </div>
          }
        />
      }
    >
      <Drawer open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <DrawerContent side="left" className="w-72 max-w-[80vw] p-0">
          <VisuallyHidden>
            <DrawerTitle>Navigation</DrawerTitle>
          </VisuallyHidden>
          <div className="flex h-16 items-center border-b border-border px-4">
            <Link href="/dashboard">
              <Logo size="md" />
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
