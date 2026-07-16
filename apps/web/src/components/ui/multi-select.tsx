"use client";

import { useId, useState } from "react";
import { Check, ChevronsUpDown, X } from "@/icons";
import { cn } from "@/lib/utils";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "./command";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

export interface MultiSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface MultiSelectProps {
  options: MultiSelectOption[];
  values: string[];
  onValuesChange: (values: string[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  /** Caps the number of chips shown before collapsing into "+N selected". */
  maxVisibleChips?: number;
}

/** Multi-value searchable select rendered as chips inside the trigger. */
export function MultiSelect({
  options,
  values,
  onValuesChange,
  placeholder = "Select options...",
  searchPlaceholder = "Search...",
  emptyText = "No results found.",
  disabled,
  className,
  maxVisibleChips = 3,
}: MultiSelectProps): React.ReactElement {
  const [open, setOpen] = useState(false);
  const listboxId = useId();

  const toggle = (optionValue: string): void => {
    onValuesChange(
      values.includes(optionValue)
        ? values.filter((v) => v !== optionValue)
        : [...values, optionValue],
    );
  };

  const selectedOptions = options.filter((option) => values.includes(option.value));
  const visible = selectedOptions.slice(0, maxVisibleChips);
  const overflow = selectedOptions.length - visible.length;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          disabled={disabled}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          className={cn(
            "flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-card px-2.5 py-1.5",
            "text-body-md transition-colors duration-fast ease-standard",
            "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
        >
          {selectedOptions.length === 0 && <span className="text-muted-foreground">{placeholder}</span>}
          {visible.map((option) => (
            <span
              key={option.value}
              className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-body-sm text-secondary-foreground"
            >
              {option.label}
              <span
                role="button"
                tabIndex={-1}
                onClick={(event) => {
                  event.stopPropagation();
                  toggle(option.value);
                }}
                className="rounded-sm hover:text-danger"
                aria-label={`Remove ${option.label}`}
              >
                <X className="size-3" />
              </span>
            </span>
          ))}
          {overflow > 0 && (
            <span className="rounded bg-secondary px-1.5 py-0.5 text-body-sm text-secondary-foreground">
              +{overflow}
            </span>
          )}
          <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command id={listboxId}>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = values.includes(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    value={option.label}
                    disabled={option.disabled}
                    onSelect={() => toggle(option.value)}
                  >
                    <span
                      className={cn(
                        "mr-2 flex size-4 items-center justify-center rounded-sm border border-input",
                        isSelected && "border-primary bg-primary text-primary-foreground",
                      )}
                    >
                      {isSelected && <Check className="size-3" />}
                    </span>
                    {option.label}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
