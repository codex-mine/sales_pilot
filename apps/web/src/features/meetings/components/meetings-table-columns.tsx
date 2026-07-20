"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns";
import Link from "next/link";
import { DataTableColumnHeader } from "@/components/data-table";
import { Avatar } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";
import type { MeetingResponse } from "../types";
import { MeetingStatusBadge } from "./meeting-status-badge";

export function buildMeetingsTableColumns(): ColumnDef<MeetingResponse>[] {
  return [
    {
      id: "title",
      accessorFn: (meeting) => meeting.title,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Meeting" />,
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="text-body-sm font-medium text-foreground">{row.original.title}</span>
          {row.original.lead_full_name && (
            <Link
              href={`/leads/${row.original.lead_id}`}
              className="truncate text-caption text-muted-foreground hover:underline"
              onClick={(event) => event.stopPropagation()}
            >
              {row.original.lead_full_name}
              {row.original.lead_company_name && ` · ${row.original.lead_company_name}`}
            </Link>
          )}
        </div>
      ),
    },
    {
      id: "status",
      accessorFn: (meeting) => meeting.status,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      cell: ({ row }) => <MeetingStatusBadge status={row.original.status} />,
    },
    {
      id: "owner",
      accessorFn: (meeting) => meeting.owner?.full_name ?? "",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Owner" />,
      cell: ({ row }) => {
        const owner = row.original.owner;
        if (!owner) return <span className="text-body-sm text-muted-foreground">Unassigned</span>;
        return (
          <div className="flex items-center gap-2">
            <Avatar size="xs" fallback={getInitials(owner.full_name)} />
            <span className="truncate text-body-sm text-foreground">{owner.full_name}</span>
          </div>
        );
      },
    },
    {
      id: "scheduled_start",
      accessorFn: (meeting) => meeting.scheduled_start ?? "",
      header: ({ column }) => <DataTableColumnHeader column={column} title="When" />,
      cell: ({ row }) => (
        <span className="text-body-sm text-foreground">
          {row.original.scheduled_start ? format(new Date(row.original.scheduled_start), "PPp") : "Not yet booked"}
        </span>
      ),
    },
    {
      id: "duration_minutes",
      accessorFn: (meeting) => meeting.duration_minutes,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Duration" />,
      cell: ({ row }) => <span className="text-body-sm text-foreground">{row.original.duration_minutes} min</span>,
    },
  ];
}
