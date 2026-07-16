import type { Column } from "@tanstack/react-table";
import { ArrowUpDown, ChevronDown, ChevronUp } from "@/icons";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface DataTableColumnHeaderProps<TData, TValue> {
  column: Column<TData, TValue>;
  title: string;
  className?: string;
}

/** A sortable column header button — shows the current sort direction and toggles it on click. */
export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
  className,
}: DataTableColumnHeaderProps<TData, TValue>): React.ReactElement {
  if (!column.getCanSort()) {
    return <div className={cn("text-caption font-medium text-muted-foreground", className)}>{title}</div>;
  }

  const sorted = column.getIsSorted();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => column.toggleSorting(sorted === "asc")}
      className={cn("-ml-3 h-8 gap-1.5 px-2 text-caption font-medium text-muted-foreground hover:text-foreground", className)}
    >
      {title}
      {sorted === "asc" ? (
        <ChevronUp className="size-3.5" />
      ) : sorted === "desc" ? (
        <ChevronDown className="size-3.5" />
      ) : (
        <ArrowUpDown className="size-3.5 opacity-50" />
      )}
    </Button>
  );
}
