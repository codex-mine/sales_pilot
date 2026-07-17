"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type RowSelectionState,
  type SortingState,
} from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { DataTableToolbar } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Archive, ArchiveRestore, Building2, Download, Trash2, UserCog } from "@/icons";
import { AssignOwnerDialog } from "@/features/leads/components/assign-owner-dialog";
import { useOrganizationMembers } from "@/features/organizations/hooks/use-organization-members";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useBulkCompanies } from "../hooks/use-bulk-companies";
import { useCompanies } from "../hooks/use-companies";
import { useCompanyTags } from "../hooks/use-company-tags";
import { useExportCompanies } from "../hooks/use-company-export";
import { useDeleteCompany, useToggleCompanyArchived, useUpdateCompany } from "../hooks/use-company-mutations";
import { COMPANY_STATUS_CHOICES, COMPANY_STATUS_LABELS, type CompaniesQuery, type CompanyResponse } from "../types";
import { buildCompaniesTableColumns } from "./companies-table-columns";
import { CompaniesTablePagination } from "./companies-table-pagination";

const STATUS_OPTIONS: MultiSelectOption[] = COMPANY_STATUS_CHOICES.map((status) => ({
  value: status,
  label: COMPANY_STATUS_LABELS[status],
}));

export interface CompaniesTableProps {
  onEditCompany: (company: CompanyResponse) => void;
  onCreateCompany: () => void;
}

export function CompaniesTable({ onEditCompany, onCreateCompany }: CompaniesTableProps): React.ReactElement {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [assignOwnerCompanyIds, setAssignOwnerCompanyIds] = useState<string[] | null>(null);

  const deleteConfirm = useConfirmDialog();
  const bulkDeleteConfirm = useConfirmDialog();
  const [pendingDeleteCompany, setPendingDeleteCompany] = useState<CompanyResponse | null>(null);

  const query: CompaniesQuery = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      status: statusFilter.length ? statusFilter : undefined,
      tag: tagFilter.length ? tagFilter : undefined,
      archived: showArchived ? true : undefined,
      sort_by: (sorting[0]?.id as CompaniesQuery["sort_by"]) ?? "created_at",
      sort_desc: sorting[0]?.desc ?? true,
      page,
      page_size: pageSize,
    }),
    [debouncedSearch, statusFilter, tagFilter, showArchived, sorting, page, pageSize],
  );

  const { companies, meta, isLoading } = useCompanies(query);
  const { tags } = useCompanyTags();
  const { members } = useOrganizationMembers();
  const { toggleArchived } = useToggleCompanyArchived();
  const { deleteCompany, isDeleting } = useDeleteCompany();
  const { bulkAction, isRunning: isBulkRunning } = useBulkCompanies();
  const { exportCompanies, isExporting } = useExportCompanies();
  const { updateCompany } = useUpdateCompany();

  const tagOptions: MultiSelectOption[] = tags.map((tag) => ({ value: tag.name, label: tag.name }));

  const selectedCompanyIds = Object.keys(rowSelection).filter((id) => rowSelection[id]);

  const columns = useMemo(
    () =>
      buildCompaniesTableColumns({
        onToggleArchived: toggleArchived,
        onEdit: onEditCompany,
        onDelete: (company) => {
          setPendingDeleteCompany(company);
          deleteConfirm.open();
        },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- action callbacks are stable enough for column defs
    [onEditCompany],
  );

  const table = useReactTable({
    data: companies,
    columns,
    state: { sorting, rowSelection },
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    pageCount: Math.max(Math.ceil(meta.total / meta.page_size), 1),
    enableRowSelection: true,
    getRowId: (row) => row.id,
    onSortingChange: (updater) => {
      setSorting(updater);
      setPage(1);
    },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
  });

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDeleteCompany) return;
    await deleteCompany(pendingDeleteCompany.id);
    deleteConfirm.close();
    setPendingDeleteCompany(null);
  }

  async function handleBulkDelete(): Promise<void> {
    await bulkAction({ company_ids: selectedCompanyIds, action: "delete" });
    setRowSelection({});
    bulkDeleteConfirm.close();
  }

  async function handleBulkArchive(archived: boolean): Promise<void> {
    await bulkAction({ company_ids: selectedCompanyIds, action: archived ? "archive" : "restore" });
    setRowSelection({});
  }

  const visibleColumnCount = table.getVisibleFlatColumns().length;

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card">
      <DataTableToolbar
        table={table}
        searchValue={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        searchPlaceholder="Search name, website, industry, notes..."
        filters={
          <>
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
            <MultiSelect
              options={tagOptions}
              values={tagFilter}
              onValuesChange={(values) => {
                setTagFilter(values);
                setPage(1);
              }}
              placeholder="Tags"
              className="w-40"
            />
            <Button
              type="button"
              variant={showArchived ? "soft" : "outline"}
              size="sm"
              onClick={() => {
                setShowArchived((v) => !v);
                setPage(1);
              }}
            >
              <Archive className="size-4" />
              Archived
            </Button>
          </>
        }
        bulkActions={
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => setAssignOwnerCompanyIds(selectedCompanyIds)}>
              <UserCog className="size-4" />
              Assign owner
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleBulkArchive(!showArchived)}>
              {showArchived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {showArchived ? "Restore" : "Archive"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void exportCompanies({ company_ids: selectedCompanyIds })}
              isLoading={isExporting}
            >
              <Download className="size-4" />
              Export
            </Button>
            <Button variant="ghost" size="sm" className="text-danger" onClick={bulkDeleteConfirm.open}>
              <Trash2 className="size-4" />
              Delete
            </Button>
          </div>
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
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  className="cursor-pointer"
                  onClick={() => router.push(`/companies/${row.original.id}`)}
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
                    icon={Building2}
                    title="No companies yet"
                    description="Create your first company to get started."
                    action={
                      <Button size="sm" onClick={onCreateCompany}>
                        Create company
                      </Button>
                    }
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <CompaniesTablePagination
        meta={meta}
        selectedCount={selectedCompanyIds.length}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
      />

      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this company?"
        description={`This permanently deletes "${pendingDeleteCompany?.name ?? "this company"}". This cannot be undone.`}
        confirmLabel="Delete company"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
      <ConfirmDialog
        open={bulkDeleteConfirm.isOpen}
        onOpenChange={bulkDeleteConfirm.onOpenChange}
        title={`Delete ${selectedCompanyIds.length} compan${selectedCompanyIds.length === 1 ? "y" : "ies"}?`}
        description="This permanently deletes the selected companies. This cannot be undone."
        confirmLabel="Delete companies"
        isConfirming={isBulkRunning}
        onConfirm={handleBulkDelete}
      />
      <AssignOwnerDialog
        open={assignOwnerCompanyIds !== null}
        onOpenChange={(open) => !open && setAssignOwnerCompanyIds(null)}
        members={members}
        onAssign={async (ownerId) => {
          if (!assignOwnerCompanyIds) return;
          if (assignOwnerCompanyIds.length === 1) {
            await updateCompany({ companyId: assignOwnerCompanyIds[0]!, payload: { owner_id: ownerId } });
          } else {
            await bulkAction({ company_ids: assignOwnerCompanyIds, action: "assign_owner", owner_id: ownerId });
          }
          setAssignOwnerCompanyIds(null);
          setRowSelection({});
        }}
      />
    </div>
  );
}
