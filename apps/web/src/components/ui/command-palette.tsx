"use client";

import { useEffect, type ReactNode } from "react";
import type { IconComponent } from "@/icons";
import { useDisclosure } from "@/hooks/use-disclosure";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "./command";

export interface CommandPaletteItem {
  id: string;
  label: string;
  icon?: IconComponent;
  shortcut?: string;
  onSelect: () => void;
}

export interface CommandPaletteGroup {
  heading: string;
  items: CommandPaletteItem[];
}

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  groups: CommandPaletteGroup[];
  placeholder?: string;
  emptyText?: string;
  footer?: ReactNode;
}

/** The ⌘K global command palette. Compose `groups` from whatever actions/navigation the current page exposes. */
export function CommandPalette({
  open,
  onOpenChange,
  groups,
  placeholder = "Type a command or search...",
  emptyText = "No results found.",
}: CommandPaletteProps): React.ReactElement {
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder={placeholder} />
      <CommandList>
        <CommandEmpty>{emptyText}</CommandEmpty>
        {groups.map((group, index) => (
          <div key={group.heading}>
            <CommandGroup heading={group.heading}>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <CommandItem
                    key={item.id}
                    onSelect={() => {
                      item.onSelect();
                      onOpenChange(false);
                    }}
                  >
                    {Icon && <Icon className="size-4" />}
                    {item.label}
                    {item.shortcut && <CommandShortcut>{item.shortcut}</CommandShortcut>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {index < groups.length - 1 && <CommandSeparator />}
          </div>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

/** Manages open state + registers the global ⌘K / Ctrl+K shortcut to toggle it. */
export function useCommandPalette(): ReturnType<typeof useDisclosure> {
  const disclosure = useDisclosure(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        disclosure.toggle();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [disclosure]);

  return disclosure;
}
