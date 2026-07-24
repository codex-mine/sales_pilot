"use client";

import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { DataTableToolbar } from "@/components/data-table";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Mail } from "@/icons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useDeleteEmailTemplate, useDuplicateEmailTemplate } from "../hooks/use-email-template-mutations";
import { useEmailTemplates } from "../hooks/use-email-templates";
import {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateResponse,
  type EmailTemplatesQuery,
} from "../types";
import { buildEmailTemplatesTableColumns } from "./email-templates-table-columns";
import { EmailTemplateFormDrawer } from "./email-template-form-drawer";
import { EmailTemplatePreviewDialog } from "./email-template-preview-dialog";

const TYPE_OPTIONS: MultiSelectOption[] = EMAIL_TEMPLATE_TYPE_CHOICES.map((type) => ({
  value: type,
  label: EMAIL_TEMPLATE_TYPE_LABELS[type],
}));
const TONE_OPTIONS: MultiSelectOption[] = EMAIL_TONE_CHOICES.map((tone) => ({
  value: tone,
  label: EMAIL_TONE_LABELS[tone],
}));

export function EmailTemplatesTable(): React.ReactElement {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [toneFilter, setToneFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplateResponse | undefined>(undefined);
  const [previewingTemplate, setPreviewingTemplate] = useState<EmailTemplateResponse | undefined>(undefined);
  const [pendingDelete, setPendingDelete] = useState<EmailTemplateResponse | null>(null);
  const deleteConfirm = useConfirmDialog();

  const query: EmailTemplatesQuery = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      template_type: typeFilter.length ? typeFilter : undefined,
      tone: toneFilter.length ? toneFilter : undefined,
      page,
      page_size: 25,
    }),
    [debouncedSearch, typeFilter, toneFilter, page],
  );

  const { templates, meta, isLoading } = useEmailTemplates(query);
  const { deleteTemplate, isDeleting } = useDeleteEmailTemplate();
  const { duplicateTemplate } = useDuplicateEmailTemplate();

  const columns = useMemo(
    () =>
      buildEmailTemplatesTableColumns({
        onPreview: setPreviewingTemplate,
        onEdit: setEditingTemplate,
        onDuplicate: (template) => void duplicateTemplate(template.id),
        onDelete: (template) => {
          setPendingDelete(template);
          deleteConfirm.open();
        },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- action callbacks are stable enough for column defs
    [],
  );

  const table = useReactTable({
    data: templates,
    columns,
    manualPagination: true,
    manualFiltering: true,
    pageCount: Math.max(Math.ceil(meta.total / meta.page_size), 1),
    getCoreRowModel: getCoreRowModel(),
  });

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDelete) return;
    await deleteTemplate(pendingDelete.id);
    deleteConfirm.close();
    setPendingDelete(null);
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
        searchPlaceholder="Search name or subject..."
        filters={
          <>
            <MultiSelect
              options={TYPE_OPTIONS}
              values={typeFilter}
              onValuesChange={(values) => {
                setTypeFilter(values);
                setPage(1);
              }}
              placeholder="Type"
              className="w-40"
            />
            <MultiSelect
              options={TONE_OPTIONS}
              values={toneFilter}
              onValuesChange={(values) => {
                setToneFilter(values);
                setPage(1);
              }}
              placeholder="Tone"
              className="w-40"
            />
          </>
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
              Array.from({ length: 6 }).map((_, rowIndex) => (
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
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={visibleColumnCount} className="h-64">
                  <EmptyState
                    icon={Mail}
                    title="No email templates yet"
                    description="Create one from scratch, or approve an AI-generated email and save it as a template."
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <p className="text-body-sm text-muted-foreground">{meta.total} template(s)</p>
        <Pagination page={page} pageCount={Math.max(Math.ceil(meta.total / meta.page_size), 1)} onPageChange={setPage} />
      </div>

      <EmailTemplateFormDrawer
        open={Boolean(editingTemplate)}
        onOpenChange={(open) => !open && setEditingTemplate(undefined)}
        template={editingTemplate}
      />
      <EmailTemplatePreviewDialog
        open={Boolean(previewingTemplate)}
        onOpenChange={(open) => !open && setPreviewingTemplate(undefined)}
        template={previewingTemplate}
      />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this email template?"
        description={`This permanently deletes "${pendingDelete?.name ?? "this template"}". This cannot be undone.`}
        confirmLabel="Delete template"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
