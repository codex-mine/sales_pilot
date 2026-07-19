"use client";

import { flexRender, getCoreRowModel, useReactTable, type SortingState } from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { DataTableToolbar } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Rocket } from "@/icons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useCampaignStatusControl, useDeleteCampaign } from "../hooks/use-campaign-mutations";
import { useCampaigns } from "../hooks/use-campaigns";
import { CAMPAIGN_STATUS_CHOICES, CAMPAIGN_STATUS_LABELS, type CampaignResponse, type CampaignsQuery } from "../types";
import { buildCampaignsTableColumns } from "./campaigns-table-columns";
import { CampaignsTablePagination } from "./campaigns-table-pagination";

const STATUS_OPTIONS: MultiSelectOption[] = CAMPAIGN_STATUS_CHOICES.map((status) => ({
  value: status,
  label: CAMPAIGN_STATUS_LABELS[status],
}));

export interface CampaignsTableProps {
  onEditCampaign: (campaign: CampaignResponse) => void;
  onCreateCampaign: () => void;
}

export function CampaignsTable({ onEditCampaign, onCreateCampaign }: CampaignsTableProps): React.ReactElement {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [pendingDeleteCampaign, setPendingDeleteCampaign] = useState<CampaignResponse | null>(null);
  const deleteConfirm = useConfirmDialog();

  const query: CampaignsQuery = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      status: statusFilter.length ? statusFilter : undefined,
      page,
      page_size: pageSize,
    }),
    [debouncedSearch, statusFilter, page, pageSize],
  );

  const { campaigns, meta, isLoading } = useCampaigns(query);
  const { activateCampaign, pauseCampaign, archiveCampaign } = useCampaignStatusControl();
  const { deleteCampaign, isDeleting } = useDeleteCampaign();

  const columns = useMemo(
    () =>
      buildCampaignsTableColumns({
        onEdit: onEditCampaign,
        onActivate: (campaign) => void activateCampaign(campaign.id),
        onPause: (campaign) => void pauseCampaign(campaign.id),
        onArchive: (campaign) => void archiveCampaign(campaign.id),
        onDelete: (campaign) => {
          setPendingDeleteCampaign(campaign);
          deleteConfirm.open();
        },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- action callbacks are stable enough for column defs
    [onEditCampaign],
  );

  const table = useReactTable({
    data: campaigns,
    columns,
    state: { sorting },
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    pageCount: Math.max(Math.ceil(meta.total / meta.page_size), 1),
    onSortingChange: (updater) => {
      setSorting(updater);
      setPage(1);
    },
    getCoreRowModel: getCoreRowModel(),
  });

  const visibleColumnCount = table.getVisibleFlatColumns().length;

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDeleteCampaign) return;
    await deleteCampaign(pendingDeleteCampaign.id);
    deleteConfirm.close();
    setPendingDeleteCampaign(null);
  }

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card">
      <DataTableToolbar
        table={table}
        searchValue={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        searchPlaceholder="Search campaign name..."
        filters={
          <MultiSelect
            options={STATUS_OPTIONS}
            values={statusFilter}
            onValuesChange={(values) => {
              setStatusFilter(values);
              setPage(1);
            }}
            placeholder="Status"
            className="w-40"
          />
        }
      />
      <div className="max-h-[36rem] overflow-auto">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, rowIndex) => (
                <TableRow key={rowIndex}>
                  {Array.from({ length: visibleColumnCount }).map((__, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-4 w-full max-w-32" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/campaigns/${row.original.id}`)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={visibleColumnCount} className="h-64">
                  <EmptyState
                    icon={Rocket}
                    title="No campaigns yet"
                    description="Create your first campaign to start a multi-step outreach sequence."
                    action={
                      <Button size="sm" onClick={onCreateCampaign}>
                        Create campaign
                      </Button>
                    }
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <CampaignsTablePagination
        meta={meta}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
      />

      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this campaign?"
        description={`This permanently deletes "${pendingDeleteCampaign?.name ?? "this campaign"}". This cannot be undone.`}
        confirmLabel="Delete campaign"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
