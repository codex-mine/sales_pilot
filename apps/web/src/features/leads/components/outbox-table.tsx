"use client";

import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { DataTableToolbar } from "@/components/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Inbox } from "@/icons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useCancelScheduledEmail, useEmailOutbox, useSendEmail } from "../hooks/use-lead-sending";
import type { OutboxEmailResponse } from "../types";
import { buildOutboxTableColumns } from "./outbox-table-columns";
import { EmailPreviewDialog } from "./email-preview-dialog";

const STATUS_OPTIONS: MultiSelectOption[] = [
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "sending", label: "Sending" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "bounced", label: "Bounced" },
];

export function OutboxTable(): React.ReactElement {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [previewEmail, setPreviewEmail] = useState<OutboxEmailResponse | null>(null);

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      status: statusFilter.length ? statusFilter : undefined,
      page,
      page_size: 25,
    }),
    [debouncedSearch, statusFilter, page],
  );

  const { emails, meta, isLoading } = useEmailOutbox(query);
  const { sendEmail } = useSendEmail();
  const { cancelEmail } = useCancelScheduledEmail();

  const columns = useMemo(
    () =>
      buildOutboxTableColumns({
        onSend: (email) => void sendEmail({ leadId: email.lead_id, emailId: email.id }),
        onCancel: (email) => void cancelEmail({ leadId: email.lead_id, emailId: email.id }),
        onPreview: (email) => setPreviewEmail(email),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- action callbacks are stable enough for column defs
    [],
  );

  const table = useReactTable({
    data: emails,
    columns,
    manualPagination: true,
    manualFiltering: true,
    pageCount: Math.max(Math.ceil(meta.total / meta.page_size), 1),
    getCoreRowModel: getCoreRowModel(),
  });

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
        searchPlaceholder="Search subject or recipient..."
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
                    icon={Inbox}
                    title="No emails yet"
                    description="Approved drafts, scheduled sends, and sent emails across all your leads show up here."
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <p className="text-body-sm text-muted-foreground">{meta.total} email(s)</p>
        <Pagination page={page} pageCount={Math.max(Math.ceil(meta.total / meta.page_size), 1)} onPageChange={setPage} />
      </div>

      <EmailPreviewDialog
        open={Boolean(previewEmail)}
        onOpenChange={(open) => !open && setPreviewEmail(null)}
        emailId={previewEmail?.id}
      />
    </div>
  );
}
