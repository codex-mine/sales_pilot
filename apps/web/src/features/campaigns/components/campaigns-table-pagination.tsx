import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { PaginationMeta } from "../types";

export interface CampaignsTablePaginationProps {
  meta: PaginationMeta;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  pageSizeOptions?: number[];
}

export function CampaignsTablePagination({
  meta,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100, 200],
}: CampaignsTablePaginationProps): React.ReactElement {
  const pageCount = Math.max(Math.ceil(meta.total / meta.page_size), 1);

  return (
    <div className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-body-sm text-muted-foreground">{meta.total} campaign(s) total.</p>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-body-sm text-muted-foreground">Rows per page</span>
          <Select value={String(meta.page_size)} onValueChange={(value) => onPageSizeChange(Number(value))}>
            <SelectTrigger className="h-8 w-[4.5rem]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <span className="text-body-sm text-muted-foreground">
          Page {meta.page} of {pageCount}
        </span>
        <Pagination page={meta.page} pageCount={pageCount} onPageChange={onPageChange} />
      </div>
    </div>
  );
}
