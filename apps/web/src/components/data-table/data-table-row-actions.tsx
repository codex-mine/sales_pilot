import type { ReactNode } from "react";
import { MoreHorizontal } from "@/icons";
import { IconButton } from "@/components/ui/icon-button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export interface DataTableRowActionsProps {
  /** Compose with `DropdownMenuItem` (see dropdown-menu.tsx). */
  children: ReactNode;
}

/** Standard "⋯" trailing-column row-actions menu for a DataTable row. */
export function DataTableRowActions({ children }: DataTableRowActionsProps): React.ReactElement {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton
          icon={MoreHorizontal}
          aria-label="Row actions"
          variant="ghost"
          size="sm"
          onClick={(event) => event.stopPropagation()}
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">{children}</DropdownMenuContent>
    </DropdownMenu>
  );
}
