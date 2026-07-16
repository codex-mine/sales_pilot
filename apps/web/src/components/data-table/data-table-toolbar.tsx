import type { Table } from "@tanstack/react-table";
import type { ReactNode } from "react";
import { Columns3 } from "@/icons";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SearchInput } from "@/components/ui/search-input";

export interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  /** Bound to the table's global filter — pass the controlled search string. */
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  /** Rendered when 1+ rows are selected (e.g. "Delete", "Export" buttons). */
  bulkActions?: ReactNode;
  /** Extra filter controls (Select/Combobox) rendered next to the search box. */
  filters?: ReactNode;
}

/** DataTable header row: search, custom filters, column visibility toggle, and a bulk-actions bar when rows are selected. */
export function DataTableToolbar<TData>({
  table,
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search...",
  bulkActions,
  filters,
}: DataTableToolbarProps<TData>): React.ReactElement {
  const selectedCount = table.getFilteredSelectedRowModel().rows.length;

  return (
    <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-1 items-center gap-2">
        <SearchInput
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          onClear={() => onSearchChange("")}
          placeholder={searchPlaceholder}
          className="max-w-xs"
        />
        {filters}
      </div>
      <div className="flex items-center gap-2">
        {selectedCount > 0 && bulkActions && (
          <div className="flex items-center gap-2 rounded-md bg-accent px-3 py-1.5 text-body-sm font-medium text-accent-foreground">
            {selectedCount} selected
            {bulkActions}
          </div>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Columns3 className="size-4" />
              View
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {table
              .getAllColumns()
              .filter((column) => column.getCanHide())
              .map((column) => (
                <DropdownMenuCheckboxItem
                  key={column.id}
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(!!value)}
                  onSelect={(event) => event.preventDefault()}
                >
                  {column.id}
                </DropdownMenuCheckboxItem>
              ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
