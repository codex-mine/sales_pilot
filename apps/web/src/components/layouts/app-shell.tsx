"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Bell,
  Bot,
  Briefcase,
  Building2,
  CalendarDays,
  FileText,
  History,
  Inbox,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  MessagesSquare,
  Rocket,
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
import { useMarkAllNotificationsRead, useMarkNotificationRead } from "@/features/notifications/hooks/use-notification-mutations";
import { useNotifications } from "@/features/notifications/hooks/use-notifications";
import { useUnreadNotificationCount } from "@/features/notifications/hooks/use-unread-notification-count";
import type { NotificationResponse } from "@/features/notifications/types";
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
  { href: "/meetings", label: "Meetings", icon: CalendarDays },
  { href: "/campaigns", label: "Campaigns", icon: Rocket },
  { href: "/reports", label: "Reports", icon: FileText },
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
      { href: "/settings/calendar", label: "Calendar", icon: CalendarDays },
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
            // "Leads", "Companies", and "Campaigns" have sub-routes
            // (/leads/[id], /leads/import, /companies/[id], /campaigns/[id],
            // ...) without their own nav entries, so they need prefix
            // matching to stay highlighted there; every other item maps 1:1
            // to a literal href.
            isActive={
              entry.href === "/leads" || entry.href === "/companies" || entry.href === "/campaigns"
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

/** Notification bell — recent notifications with unread indicators, "Mark
 * all read", and click-through to each notification's `action_url` (already
 * populated by the modules that write these rows: inbox replies, meeting
 * bookings, campaign approvals/tasks). Unread badge polls per
 * `useUnreadNotificationCount`. */
function NotificationsQuickMenu(): React.ReactElement {
  const router = useRouter();
  const { count } = useUnreadNotificationCount();
  const { notifications, isLoading } = useNotifications(false, 1, 8);
  const { markRead } = useMarkNotificationRead();
  const { markAllRead, isMarkingAll } = useMarkAllNotificationsRead();

  function handleClick(notification: NotificationResponse): void {
    if (!notification.is_read) void markRead(notification.id);
    if (notification.action_url) router.push(notification.action_url);
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className={HEADER_ICON_BUTTON_CLASS} aria-label={count > 0 ? `Notifications — ${count} unread` : "Notifications"}>
          <Bell className="size-4" />
          <UnreadCountBadge count={count} />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-2 py-1.5">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {count > 0 && (
            <button
              type="button"
              onClick={() => void markAllRead()}
              disabled={isMarkingAll}
              className="text-caption text-primary hover:underline disabled:opacity-50"
            >
              Mark all read
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        {isLoading ? (
          <div className="px-4 py-8 text-center text-body-sm text-muted-foreground">Loading...</div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
            <Bell className="size-6 text-muted-foreground" />
            <p className="text-body-sm text-muted-foreground">You&apos;re all caught up.</p>
          </div>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            {notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => handleClick(notification)}
                className="flex w-full flex-col gap-0.5 px-2 py-2 text-left transition-colors hover:bg-muted"
              >
                <div className="flex items-center gap-2">
                  {!notification.is_read && <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />}
                  <span className="truncate text-body-sm font-medium text-foreground">{notification.title}</span>
                </div>
                {notification.body && (
                  <p className="line-clamp-2 pl-3.5 text-caption text-muted-foreground">{notification.body}</p>
                )}
              </button>
            ))}
          </div>
        )}
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
