"use client";

import { Slot } from "@radix-ui/react-slot";
import { AnimatePresence, motion } from "framer-motion";
import {
  createContext,
  useContext,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from "react";
import { PanelLeftClose, PanelLeft, type IconComponent } from "@/icons";
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
        "sticky top-0 flex h-screen shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-sidebar",
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
    <div className={cn("flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border px-4", className)}>
      {children}
    </div>
  );
}

export function SidebarContent({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("flex-1 overflow-y-auto px-3 py-4", className)}>{children}</div>;
}

export function SidebarFooter({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <div className={cn("shrink-0 border-t border-sidebar-border p-3", className)}>{children}</div>;
}

export function SidebarNav({ className, children }: { className?: string; children: ReactNode }): React.ReactElement {
  return <nav className={cn("flex flex-col gap-1", className)}>{children}</nav>;
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
  const Comp = asChild ? Slot : "a";

  const content = (
    <Comp
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "group flex h-9 items-center gap-3 rounded-md px-3 text-body-sm font-medium transition-colors duration-fast ease-standard",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/70",
        isCollapsed && "justify-center px-0",
        className,
      )}
      {...props}
    >
      <Icon className="size-4 shrink-0" />
      {!isCollapsed && <span className="flex-1 truncate">{label}</span>}
      {!isCollapsed && badge}
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

export function SidebarTrigger({ className }: { className?: string }): React.ReactElement {
  const { isCollapsed, toggle } = useSidebarContext();

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      className={cn(
        "flex size-8 items-center justify-center rounded-md text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
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
