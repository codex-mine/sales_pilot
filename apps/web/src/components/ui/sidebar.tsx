"use client";

import { Slot } from "@radix-ui/react-slot";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from "react";
import { ChevronDown, PanelLeftClose, PanelLeft, type IconComponent } from "@/icons";
import { useBreakpoint } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";
import { duration, easing } from "@/motion/tokens";
import { Tooltip, TooltipContent, TooltipTrigger } from "./tooltip";

const EXPANDED_WIDTH = 272;
const COLLAPSED_WIDTH = 72;

interface SidebarContextValue {
  isCollapsed: boolean;
  toggle: () => void;
  isDesktop: boolean;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

function useSidebarContext(): SidebarContextValue {
  const context = useContext(SidebarContext);
  if (!context) throw new Error("Sidebar components must be used within <SidebarProvider>.");
  return context;
}

export interface SidebarProviderProps {
  children: ReactNode;
  defaultCollapsed?: boolean;
}

export function SidebarProvider({ children, defaultCollapsed = false }: SidebarProviderProps): React.ReactElement {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const isDesktop = useBreakpoint("lg");

  return (
    <SidebarContext.Provider
      value={{ isCollapsed: isDesktop ? isCollapsed : false, toggle: () => setIsCollapsed((c) => !c), isDesktop }}
    >
      <div className="flex min-h-screen w-full">{children}</div>
    </SidebarContext.Provider>
  );
}

export function Sidebar({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  const { isCollapsed, isDesktop } = useSidebarContext();

  return (
    <motion.aside
      animate={{ width: isDesktop ? (isCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH) : EXPANDED_WIDTH }}
      transition={{ duration: duration.normal, ease: easing.standard }}
      className={cn(
        // Borderless rail: the soft `shadow-sidebar` plus the tinted canvas
        // separates it from content (dark mode keeps a hairline border since
        // its shadows are near-invisible).
        "sticky top-0 z-40 flex h-screen shrink-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground shadow-sidebar dark:border-r dark:border-sidebar-border",
        !isDesktop && "hidden",
        className,
      )}
    >
      {children}
    </motion.aside>
  );
}

export function SidebarHeader({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return (
    <div className={cn("flex h-16 shrink-0 items-center gap-2 px-6", className)}>
      {children}
    </div>
  );
}

export function SidebarContent({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("flex-1 overflow-y-auto px-4 py-6", className)}>{children}</div>;
}

export function SidebarFooter({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("shrink-0 border-t border-sidebar-border p-4", className)}>{children}</div>;
}

export function SidebarNav({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <nav className={cn("flex flex-col gap-2", className)}>{children}</nav>;
}

export function SidebarNavGroup({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("flex flex-col gap-1 py-2", className)}>{children}</div>;
}

export function SidebarNavGroupLabel({ children }: { children: ReactNode }): React.ReactElement {
  const { isCollapsed } = useSidebarContext();
  if (isCollapsed) return <div className="my-2 h-px bg-sidebar-border" aria-hidden="true" />;
  return (
    <div className="px-3 pb-1 text-caption font-medium uppercase tracking-wide text-sidebar-foreground/50">
      {children}
    </div>
  );
}

export interface SidebarNavItemProps extends Omit<ComponentPropsWithoutRef<"a">, "href"> {
  icon: IconComponent;
  label: string;
  href: string;
  isActive?: boolean;
  badge?: ReactNode;
  asChild?: boolean;
}

export function SidebarNavItem({
  icon: Icon,
  label,
  href,
  isActive,
  badge,
  asChild,
  className,
  ...props
}: SidebarNavItemProps): React.ReactElement {
  const { isCollapsed } = useSidebarContext();
  // Client-side navigation is the point of an SPA sidebar — a raw <a> here
  // would force a full browser reload on every nav click, so the
  // non-`asChild` path renders next/link instead of a plain anchor.
  const Comp = asChild ? Slot : Link;

  const content = (
    <Comp
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        // Active state matches the reference chrome: brand-colored icon +
        // label with a thick indicator bar hugging the sidebar's outer edge
        // (the `-right-4` cancels SidebarContent's px-4 inset) — no filled
        // pill background.
        "group relative flex h-11 items-center gap-3 rounded-md px-3 text-body-md font-medium transition-colors duration-fast ease-standard",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        isActive
          ? "font-semibold text-primary hover:bg-transparent hover:text-primary"
          : "text-sidebar-foreground/60",
        isCollapsed && "justify-center px-0",
        className,
      )}
      {...props}
    >
      <Icon className="size-5 shrink-0" />
      {!isCollapsed && <span className="flex-1 truncate">{label}</span>}
      {!isCollapsed && badge}
      {isActive && (
        <span
          aria-hidden="true"
          className="absolute -right-4 top-1/2 h-8 w-1 -translate-y-1/2 rounded-l-full bg-primary"
        />
      )}
    </Comp>
  );

  if (!isCollapsed) return content;

  return (
    <Tooltip delayDuration={300}>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  );
}

export interface SidebarNavCollapsibleItem {
  href: string;
  label: string;
  icon: IconComponent;
  isActive: boolean;
}

export interface SidebarNavCollapsibleProps {
  icon: IconComponent;
  label: string;
  items: SidebarNavCollapsibleItem[];
  /** Whether any child route is currently active — drives the parent's active styling and the initial open state. */
  isActiveGroup: boolean;
  /** Fired when a child link (or, collapsed, the group itself) is clicked — closes the mobile slide-over nav. */
  onNavigate?: () => void;
  className?: string;
}

/** A sidebar nav item that expands in place to reveal sub-routes (e.g. Settings -> Profile/Security/Organization)
 * instead of pushing them into a separate in-page sidebar. Auto-opens when one of its children is the active route;
 * collapsed (icon-only) sidebar mode skips the expand affordance and just links straight to the first child. */
export function SidebarNavCollapsible({
  icon: Icon,
  label,
  items,
  isActiveGroup,
  onNavigate,
  className,
}: SidebarNavCollapsibleProps): React.ReactElement {
  const { isCollapsed } = useSidebarContext();
  const [isOpen, setIsOpen] = useState(isActiveGroup);

  useEffect(() => {
    if (isActiveGroup) setIsOpen(true);
  }, [isActiveGroup]);

  if (isCollapsed) {
    const first = items[0];
    const content = (
      <Link
        href={first ? first.href : "#"}
        aria-current={isActiveGroup ? "page" : undefined}
        onClick={onNavigate}
        className={cn(
          "group relative flex h-11 items-center justify-center rounded-md px-0 text-body-md font-medium transition-colors duration-fast ease-standard",
          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
          isActiveGroup ? "font-semibold text-primary hover:bg-transparent hover:text-primary" : "text-sidebar-foreground/60",
          className,
        )}
      >
        <Icon className="size-5 shrink-0" />
        {isActiveGroup && (
          <span
            aria-hidden="true"
            className="absolute -right-4 top-1/2 h-8 w-1 -translate-y-1/2 rounded-l-full bg-primary"
          />
        )}
      </Link>
    );
    return (
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        className={cn(
          "group relative flex h-11 w-full items-center gap-3 rounded-md px-3 text-body-md font-medium transition-colors duration-fast ease-standard",
          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
          isActiveGroup ? "font-semibold text-primary hover:bg-transparent hover:text-primary" : "text-sidebar-foreground/60",
        )}
      >
        <Icon className="size-5 shrink-0" />
        <span className="flex-1 truncate text-left">{label}</span>
        <ChevronDown
          className={cn("size-4 shrink-0 transition-transform duration-fast ease-standard", isOpen && "rotate-180")}
        />
        {isActiveGroup && (
          <span
            aria-hidden="true"
            className="absolute -right-4 top-1/2 h-8 w-1 -translate-y-1/2 rounded-l-full bg-primary"
          />
        )}
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: duration.fast, ease: easing.standard }}
            className="overflow-hidden"
          >
            <div className="flex flex-col gap-1 py-1 pl-4">
              {items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={item.isActive ? "page" : undefined}
                  onClick={onNavigate}
                  className={cn(
                    "flex h-9 items-center gap-2.5 rounded-md px-3 text-body-sm font-medium transition-colors duration-fast ease-standard",
                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                    item.isActive ? "font-semibold text-primary" : "text-sidebar-foreground/60",
                  )}
                >
                  <item.icon className="size-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SidebarTrigger({ className }: { className?: string }): React.ReactElement {
  const { isCollapsed, toggle } = useSidebarContext();

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      className={cn(
        "flex size-8 items-center justify-center rounded-md text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        "focus-visible:!outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        className,
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isCollapsed ? "collapsed" : "expanded"}
          initial={{ opacity: 0, rotate: -90 }}
          animate={{ opacity: 1, rotate: 0 }}
          exit={{ opacity: 0, rotate: 90 }}
          transition={{ duration: duration.fast }}
          className="flex"
        >
          {isCollapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

export function useSidebar(): SidebarContextValue {
  return useSidebarContext();
}
