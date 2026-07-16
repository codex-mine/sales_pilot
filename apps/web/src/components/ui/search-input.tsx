"use client";

import { forwardRef } from "react";
import { Search, X } from "@/icons";
import { cn } from "@/lib/utils";
import { Input, type InputProps } from "./input";

export interface SearchInputProps extends Omit<InputProps, "leftIcon" | "type"> {
  /** Called when the clear (×) button is pressed. Only shown when `value` is non-empty. */
  onClear?: () => void;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, value, onClear, placeholder = "Search...", ...props }, ref) => {
    const hasValue = typeof value === "string" && value.length > 0;

    return (
      <Input
        ref={ref}
        type="search"
        value={value}
        placeholder={placeholder}
        leftIcon={<Search />}
        rightIcon={
          hasValue && onClear ? (
            <button
              type="button"
              onClick={onClear}
              className="pointer-events-auto rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Clear search"
            >
              <X className="size-3.5" />
            </button>
          ) : undefined
        }
        className={cn("[&::-webkit-search-cancel-button]:hidden", className)}
        {...props}
      />
    );
  },
);
SearchInput.displayName = "SearchInput";
