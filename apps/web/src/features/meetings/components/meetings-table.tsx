"use client";

import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { DataTableToolbar } from "@/components/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CalendarDays } from "@/icons";
import { useOrganizationMembers } from "@/features/organizations/hooks/use-organization-members";
import { useMeetings } from "../hooks/use-meetings";
import { MEETING_STATUS_CHOICES, MEETING_STATUS_LABELS, type MeetingResponse } from "../types";
import { MeetingDetailDrawer } from "./meeting-detail-drawer";
import { buildMeetingsTableColumns } from "./meetings-table-columns";

const STATUS_OPTIONS: MultiSelectOption[] = MEETING_STATUS_CHOICES.map((status) => ({
  value: status,
  label: MEETING_STATUS_LABELS[status],
}));

export function MeetingsTable(): React.ReactElement {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [ownerId, setOwnerId] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<MeetingResponse | null>(null);
  const { members } = useOrganizationMembers();

  const query = useMemo(
    () => ({
      status: statusFilter.length ? statusFilter : undefined,
      owner_id: ownerId === "all" ? undefined : ownerId,
      page,
      page_size: 25,
    }),
    [statusFilter, ownerId, page],
  );

  const { meetings, meta, isLoading } = useMeetings(query);
  const columns = useMemo(() => buildMeetingsTableColumns(), []);

  // The backend list endpoint has no full-text search param — this filters
  // only the currently loaded page, a reasonable trade-off for a "find the
  // meeting I just saw" search box rather than a full server-side search.
  const visibleMeetings = useMemo(() => {
    if (!search.trim()) return meetings;
    const needle = search.trim().toLowerCase();
    return meetings.filter(
      (meeting) =>
        meeting.title.toLowerCase().includes(needle) ||
        (meeting.lead_full_name ?? "").toLowerCase().includes(needle) ||
        (meeting.lead_company_name ?? "").toLowerCase().includes(needle),
    );
  }, [meetings, search]);

  const table = useReactTable({
    data: visibleMeetings,
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
        onSearchChange={setSearch}
        searchPlaceholder="Search meeting or lead..."
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
              className="w-44"
            />
            <Select
              value={ownerId}
              onValueChange={(value) => {
                setOwnerId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Owner" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All owners</SelectItem>
                {members.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                <TableRow key={row.id} className="cursor-pointer" onClick={() => setSelected(row.original)}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={visibleColumnCount} className="h-64">
                  <EmptyState
                    icon={CalendarDays}
                    title="No meetings yet"
                    description="Schedule a meeting from a lead's detail page to see it here."
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <p className="text-body-sm text-muted-foreground">{meta.total} meeting(s)</p>
        <Pagination page={page} pageCount={Math.max(Math.ceil(meta.total / meta.page_size), 1)} onPageChange={setPage} />
      </div>

      <MeetingDetailDrawer meeting={selected} open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)} />
    </div>
  );
}
