import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/brand/logo";
import { Card } from "@/components/ui/card";

export interface AuthCardProps {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}

/** Consistent chrome for every auth screen: brand mark, title/description, card body, optional footer link row. */
export function AuthCard({ title, description, children, footer }: AuthCardProps): React.ReactElement {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <Link href="/">
          <Logo size="lg" />
        </Link>
        <div className="flex flex-col gap-1">
          <h1 className="text-heading-3 font-semibold text-foreground">{title}</h1>
          {description && <p className="text-body-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      <Card className="w-full">{children}</Card>
      {footer && <div className="text-center text-body-sm text-muted-foreground">{footer}</div>}
    </div>
  );
}
