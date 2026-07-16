import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface SectionHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** A smaller heading for a section within a page (e.g. above a card grid or table). */
export function SectionHeader({ title, description, actions, className }: SectionHeaderProps): React.ReactElement {
  return (
    <div className={cn("flex items-center justify-between gap-4 pb-4", className)}>
      <div className="flex flex-col gap-0.5">
        <h2 className="text-heading-4 font-semibold text-foreground">{title}</h2>
        {description && <p className="text-body-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
