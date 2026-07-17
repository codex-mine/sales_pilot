"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { DataTableColumnHeader } from "@/components/data-table";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { getMediaUrl } from "@/lib/api/client";
import { getInitials } from "@/lib/utils";
import type { OrganizationMemberResponse, OrganizationMemberStatus } from "../types";

const STATUS_TONE: Record<OrganizationMemberStatus, "success" | "warning" | "danger" | "neutral"> = {
  active: "success",
  pending_verification: "warning",
  suspended: "danger",
  disabled: "danger",
  inactive: "neutral",
  deleted: "neutral",
};

const STATUS_LABEL: Record<OrganizationMemberStatus, string> = {
  active: "Active",
  pending_verification: "Pending verification",
  suspended: "Suspended",
  disabled: "Disabled",
  inactive: "Inactive",
  deleted: "Deleted",
};

export const membersTableColumns: ColumnDef<OrganizationMemberResponse>[] = [
  {
    id: "name",
    accessorFn: (member) => member.full_name,
    header: ({ column }) => <DataTableColumnHeader column={column} title="Member" />,
    cell: ({ row }) => {
      const member = row.original;
      return (
        <div className="flex items-center gap-3">
          <Avatar
            size="sm"
            src={getMediaUrl(member.avatar_url)}
            alt={member.full_name}
            fallback={getInitials(member.full_name)}
          />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-body-sm font-medium text-foreground">{member.full_name}</span>
            <span className="truncate text-caption text-muted-foreground">{member.email}</span>
          </div>
        </div>
      );
    },
  },
  {
    id: "role",
    accessorFn: (member) => member.role ?? "—",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Role" />,
    cell: ({ row }) => {
      const role = row.original.role;
      if (!role) return <span className="text-body-sm text-muted-foreground">—</span>;
      return <Badge variant="soft">{role.charAt(0).toUpperCase() + role.slice(1)}</Badge>;
    },
  },
  {
    id: "status",
    accessorFn: (member) => member.status,
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => {
      const status = row.original.status;
      return <StatusBadge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</StatusBadge>;
    },
  },
  {
    id: "joined_at",
    accessorFn: (member) => member.joined_at,
    header: ({ column }) => <DataTableColumnHeader column={column} title="Joined" />,
    cell: ({ row }) => (
      <span className="text-body-sm text-muted-foreground">
        {formatDistanceToNow(new Date(row.original.joined_at), { addSuffix: true })}
      </span>
    ),
  },
  {
    id: "last_active_at",
    accessorFn: (member) => member.last_active_at ?? "",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last active" />,
    cell: ({ row }) => {
      const lastActive = row.original.last_active_at;
      if (!lastActive) return <span className="text-body-sm text-muted-foreground">Never</span>;
      return (
        <span className="text-body-sm text-muted-foreground">
          {formatDistanceToNow(new Date(lastActive), { addSuffix: true })}
        </span>
      );
    },
  },
];
