import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  /** Rendered above the title — typically a `BreadcrumbTrail`. */
  eyebrow?: ReactNode;
  /** Right-aligned actions (primary/secondary buttons). */
  actions?: ReactNode;
  className?: string;
}

/** The title block at the top of a page: eyebrow/breadcrumb, title, description, and trailing actions. */
export function PageHeader({ title, description, eyebrow, actions, className }: PageHeaderProps): React.ReactElement {
  return (
    <div className={cn("flex flex-col gap-4 pb-6 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="flex min-w-0 flex-col gap-1.5">
        {eyebrow}
        <h1 className="text-heading-2 font-semibold tracking-tight text-foreground text-balance">{title}</h1>
        {description && <p className="max-w-2xl text-body-md text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
