import type { ReactNode } from "react";
import type { IconComponent } from "@/icons";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: IconComponent;
  action?: ReactNode;
  className?: string;
}

/** The "nothing here yet" placeholder — for empty tables, lists, and search results. */
export function EmptyState({ title, description, icon: Icon, action, className }: EmptyStateProps): React.ReactElement {
  return (
    <div
      className={cn(
        "flex min-h-48 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-8 text-center",
        className,
      )}
    >
      {Icon && (
        <span className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Icon className="size-5" />
        </span>
      )}
      <div className="flex flex-col gap-1">
        <h3 className="text-body-lg font-medium text-foreground">{title}</h3>
        {description && <p className="max-w-sm text-body-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
