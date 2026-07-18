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
import {
  Archive,
  ArchiveRestore,
  Download,
  Mail,
  Send,
  Sparkles,
  Star,
  Tag as TagIcon,
  Trash2,
  UserCog,
} from "@/icons";
import { useOrganizationMembers } from "@/features/organizations/hooks/use-organization-members";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useBulkLeads } from "../hooks/use-bulk-leads";
import { useBulkGenerateEmails } from "../hooks/use-lead-email-generation";
import { useExportLeads } from "../hooks/use-lead-import-export";
import { useBulkSendEmails } from "../hooks/use-lead-sending";
import { useBulkTriggerResearch, useTriggerLeadResearch } from "../hooks/use-lead-research";
import { useDeleteLead, useToggleLeadFlag, useUpdateLead } from "../hooks/use-lead-mutations";
import { useLeadTags } from "../hooks/use-lead-tags";
import { useLeads } from "../hooks/use-leads";
import { LEAD_STATUS_CHOICES, LEAD_STATUS_LABELS, type LeadResponse, type LeadsQuery } from "../types";
import { AssignOwnerDialog } from "./assign-owner-dialog";
import { BulkGenerateEmailsDialog } from "./bulk-generate-emails-dialog";
import { buildLeadsTableColumns } from "./leads-table-columns";
import { LeadsTablePagination } from "./leads-table-pagination";

const STATUS_OPTIONS: MultiSelectOption[] = LEAD_STATUS_CHOICES.map((status) => ({
  value: status,
  label: LEAD_STATUS_LABELS[status],
}));

export interface LeadsTableProps {
  onEditLead: (lead: LeadResponse) => void;
  onCreateLead: () => void;
}

export function LeadsTable({ onEditLead, onCreateLead }: LeadsTableProps): React.ReactElement {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [assignOwnerLeadIds, setAssignOwnerLeadIds] = useState<string[] | null>(null);
  const [bulkGenerateOpen, setBulkGenerateOpen] = useState(false);

  const deleteConfirm = useConfirmDialog();
  const bulkDeleteConfirm = useConfirmDialog();
  const [pendingDeleteLead, setPendingDeleteLead] = useState<LeadResponse | null>(null);

  const query: LeadsQuery = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      status: statusFilter.length ? statusFilter : undefined,
      tag: tagFilter.length ? tagFilter : undefined,
      favorite: showFavoritesOnly ? true : undefined,
      archived: showArchived ? true : undefined,
      sort_by: (sorting[0]?.id as LeadsQuery["sort_by"]) ?? "created_at",
      sort_desc: sorting[0]?.desc ?? true,
      page,
      page_size: pageSize,
    }),
    [debouncedSearch, statusFilter, tagFilter, showFavoritesOnly, showArchived, sorting, page, pageSize],
  );

  const { leads, meta, isLoading } = useLeads(query);
  const { tags } = useLeadTags();
  const { members } = useOrganizationMembers();
  const { toggleFavorite, toggleArchived } = useToggleLeadFlag();
  const { deleteLead, isDeleting } = useDeleteLead();
  const { bulkAction, isRunning: isBulkRunning } = useBulkLeads();
  const { exportLeads, isExporting } = useExportLeads();
  const { updateLead } = useUpdateLead();
  const { triggerResearch } = useTriggerLeadResearch();
  const { bulkTriggerResearch, isTriggering: isBulkResearching } = useBulkTriggerResearch();
  const { bulkGenerate, isGenerating: isBulkGenerating } = useBulkGenerateEmails();
  const { bulkSend, isSending: isBulkSending } = useBulkSendEmails();
  const bulkSendConfirm = useConfirmDialog();

  const tagOptions: MultiSelectOption[] = tags.map((tag) => ({ value: tag.name, label: tag.name }));

  const selectedLeadIds = Object.keys(rowSelection).filter((id) => rowSelection[id]);

  const columns = useMemo(
    () =>
      buildLeadsTableColumns({
        onToggleFavorite: toggleFavorite,
        onToggleArchived: toggleArchived,
        onEdit: onEditLead,
        onDelete: (lead) => {
          setPendingDeleteLead(lead);
          deleteConfirm.open();
        },
        onResearch: (lead) => void triggerResearch({ leadId: lead.id }),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- action callbacks are stable enough for column defs
    [onEditLead],
  );

  const table = useReactTable({
    data: leads,
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
    if (!pendingDeleteLead) return;
    await deleteLead(pendingDeleteLead.id);
    deleteConfirm.close();
    setPendingDeleteLead(null);
  }

  async function handleBulkDelete(): Promise<void> {
    await bulkAction({ lead_ids: selectedLeadIds, action: "delete" });
    setRowSelection({});
    bulkDeleteConfirm.close();
  }

  async function handleBulkArchive(archived: boolean): Promise<void> {
    await bulkAction({ lead_ids: selectedLeadIds, action: archived ? "archive" : "restore" });
    setRowSelection({});
  }

  async function handleBulkFavorite(): Promise<void> {
    await bulkAction({ lead_ids: selectedLeadIds, action: "favorite" });
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
        searchPlaceholder="Search name, email, company, phone, tags, notes..."
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
              variant={showFavoritesOnly ? "soft" : "outline"}
              size="sm"
              onClick={() => {
                setShowFavoritesOnly((v) => !v);
                setPage(1);
              }}
            >
              <Star className="size-4" />
              Favorites
            </Button>
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
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void bulkTriggerResearch(selectedLeadIds).then(() => setRowSelection({}))}
              isLoading={isBulkResearching}
            >
              <Sparkles className="size-4" />
              Research Selected
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setBulkGenerateOpen(true)}>
              <Mail className="size-4" />
              Generate Emails
            </Button>
            <Button variant="ghost" size="sm" onClick={bulkSendConfirm.open} isLoading={isBulkSending}>
              <Send className="size-4" />
              Send Approved Emails
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setAssignOwnerLeadIds(selectedLeadIds)}>
              <UserCog className="size-4" />
              Assign owner
            </Button>
            <Button variant="ghost" size="sm" onClick={handleBulkFavorite} isLoading={isBulkRunning}>
              <Star className="size-4" />
              Favorite
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleBulkArchive(!showArchived)}>
              {showArchived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {showArchived ? "Restore" : "Archive"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void exportLeads({ lead_ids: selectedLeadIds })}
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
                  onClick={() => router.push(`/leads/${row.original.id}`)}
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
                    icon={TagIcon}
                    title="No leads yet"
                    description="Create your first lead or import a CSV to get started."
                    action={
                      <Button size="sm" onClick={onCreateLead}>
                        Create lead
                      </Button>
                    }
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <LeadsTablePagination
        meta={meta}
        selectedCount={selectedLeadIds.length}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
      />

      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this lead?"
        description={`This permanently deletes "${pendingDeleteLead?.full_name ?? "this lead"}". This cannot be undone.`}
        confirmLabel="Delete lead"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
      <ConfirmDialog
        open={bulkDeleteConfirm.isOpen}
        onOpenChange={bulkDeleteConfirm.onOpenChange}
        title={`Delete ${selectedLeadIds.length} lead(s)?`}
        description="This permanently deletes the selected leads. This cannot be undone."
        confirmLabel="Delete leads"
        isConfirming={isBulkRunning}
        onConfirm={handleBulkDelete}
      />
      <ConfirmDialog
        open={bulkSendConfirm.isOpen}
        onOpenChange={bulkSendConfirm.onOpenChange}
        title={`Send approved emails to ${selectedLeadIds.length} lead(s)?`}
        description="Sends the current DRAFT email for each selected lead that has one. This is externally visible and cannot be undone — leads without an approved draft are skipped."
        confirmLabel="Send emails"
        confirmVariant="primary"
        isConfirming={isBulkSending}
        onConfirm={async () => {
          await bulkSend({ lead_ids: selectedLeadIds });
          setRowSelection({});
          bulkSendConfirm.close();
        }}
      />
      <AssignOwnerDialog
        open={assignOwnerLeadIds !== null}
        onOpenChange={(open) => !open && setAssignOwnerLeadIds(null)}
        members={members}
        onAssign={async (ownerId) => {
          if (!assignOwnerLeadIds) return;
          if (assignOwnerLeadIds.length === 1) {
            await updateLead({ leadId: assignOwnerLeadIds[0]!, payload: { owner_id: ownerId } });
          } else {
            await bulkAction({ lead_ids: assignOwnerLeadIds, action: "assign_owner", owner_id: ownerId });
          }
          setAssignOwnerLeadIds(null);
          setRowSelection({});
        }}
      />
      <BulkGenerateEmailsDialog
        open={bulkGenerateOpen}
        onOpenChange={setBulkGenerateOpen}
        leadCount={selectedLeadIds.length}
        isGenerating={isBulkGenerating}
        onGenerate={async ({ templateType, tone }) => {
          await bulkGenerate({ lead_ids: selectedLeadIds, template_type: templateType, tone });
          setRowSelection({});
        }}
      />
    </div>
  );
}
