import { ChevronLeft, ChevronRight, MoreHorizontal } from "@/icons";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { IconButton } from "./icon-button";

export interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  className?: string;
  siblingCount?: number;
}

function buildPageList(page: number, pageCount: number, siblingCount: number): (number | "ellipsis")[] {
  const totalVisible = siblingCount * 2 + 5;
  if (pageCount <= totalVisible) return Array.from({ length: pageCount }, (_, i) => i + 1);

  const left = Math.max(page - siblingCount, 2);
  const right = Math.min(page + siblingCount, pageCount - 1);

  const pages: (number | "ellipsis")[] = [1];
  if (left > 2) pages.push("ellipsis");
  for (let p = left; p <= right; p++) pages.push(p);
  if (right < pageCount - 1) pages.push("ellipsis");
  pages.push(pageCount);
  return pages;
}

/** Numbered page navigation with edge ellipses — for tables and long lists. */
export function Pagination({ page, pageCount, onPageChange, className, siblingCount = 1 }: PaginationProps): React.ReactElement {
  const pages = buildPageList(page, pageCount, siblingCount);

  return (
    <nav aria-label="Pagination" className={cn("flex items-center gap-1", className)}>
      <IconButton
        icon={ChevronLeft}
        aria-label="Previous page"
        variant="ghost"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      />
      {pages.map((item, index) =>
        item === "ellipsis" ? (
          <span key={`ellipsis-${index}`} className="flex size-8 items-center justify-center text-muted-foreground">
            <MoreHorizontal className="size-4" />
          </span>
        ) : (
          <Button
            key={item}
            variant={item === page ? "primary" : "ghost"}
            size="sm"
            className="size-8 p-0"
            aria-current={item === page ? "page" : undefined}
            onClick={() => onPageChange(item)}
          >
            {item}
          </Button>
        ),
      )}
      <IconButton
        icon={ChevronRight}
        aria-label="Next page"
        variant="ghost"
        size="sm"
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      />
    </nav>
  );
}
