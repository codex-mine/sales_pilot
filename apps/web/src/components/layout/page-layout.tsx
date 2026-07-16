import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { Container, type ContainerProps } from "./container";

export interface PageLayoutProps extends HTMLAttributes<HTMLDivElement> {
  containerSize?: ContainerProps["size"];
}

/** Standard page body wrapper: a Container with the page's consistent top/bottom padding. Use inside AppLayout's `children`. */
export function PageLayout({ containerSize = "xl", className, children, ...props }: PageLayoutProps): React.ReactElement {
  return (
    <Container size={containerSize} className={cn("py-8", className)} {...props}>
      {children}
    </Container>
  );
}
