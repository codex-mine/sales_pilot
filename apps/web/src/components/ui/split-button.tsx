import type { ReactNode } from "react";
import { ChevronDown } from "@/icons";
import { cn } from "@/lib/utils";
import { Button, buttonVariants, type ButtonProps } from "./button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "./dropdown-menu";

export interface SplitButtonProps {
  /** Primary action label + handler — the large left-hand button. */
  children: ReactNode;
  onClick?: () => void;
  variant?: ButtonProps["variant"];
  size?: ButtonProps["size"];
  disabled?: boolean;
  isLoading?: boolean;
  /** Menu content rendered inside the dropdown (compose with `DropdownMenuItem`). */
  menu: ReactNode;
  className?: string;
  menuLabel?: string;
}

/** A primary action button with an attached dropdown for related secondary actions (e.g. "Save" + "Save as draft"). */
export function SplitButton({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled,
  isLoading,
  menu,
  className,
  menuLabel = "More actions",
}: SplitButtonProps): React.ReactElement {
  return (
    <div className={cn("inline-flex", className)}>
      <Button
        variant={variant}
        size={size}
        onClick={onClick}
        disabled={disabled}
        isLoading={isLoading}
        className="rounded-r-none border-r border-r-primary-foreground/20 focus-visible:z-10"
      >
        {children}
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            disabled={disabled}
            aria-label={menuLabel}
            className={cn(
              buttonVariants({ variant, size: size === "icon" ? "icon" : undefined }),
              "rounded-l-none px-2 focus-visible:z-10",
              size === "sm" && "h-8 w-8 px-0",
              size === "md" && "h-9 w-9 px-0",
              size === "lg" && "h-11 w-11 px-0",
            )}
          >
            <ChevronDown className="size-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">{menu}</DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
