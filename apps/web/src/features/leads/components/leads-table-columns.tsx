"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { DataTableColumnHeader, DataTableRowActions } from "@/components/data-table";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Archive, ArchiveRestore, Eye, Pencil, Sparkles, Star, Trash2 } from "@/icons";
import { cn } from "@/lib/utils";
import { getInitials } from "@/lib/utils";
import { LEAD_STATUS_LABELS, type LeadResponse, type LeadStatus } from "../types";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  new: "info",
  researching: "info",
  research_done: "primary",
  contacted: "primary",
  opened: "primary",
  replied: "primary",
  qualified: "primary",
  interested: "primary",
  unqualified: "danger",
  demo_scheduled: "warning",
  proposal: "warning",
  negotiation: "warning",
  won: "success",
  lost: "danger",
  bounced: "danger",
  unsubscribed: "danger",
};

export interface LeadsTableActions {
  onToggleFavorite: (lead: LeadResponse) => void;
  onToggleArchived: (lead: LeadResponse) => void;
  onEdit: (lead: LeadResponse) => void;
  onDelete: (lead: LeadResponse) => void;
  onResearch: (lead: LeadResponse) => void;
}

export function buildLeadsTableColumns(actions: LeadsTableActions): ColumnDef<LeadResponse>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          indeterminate={table.getIsSomePageRowsSelected() && !table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
          onClick={(event) => event.stopPropagation()}
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          onClick={(event) => event.stopPropagation()}
          aria-label="Select row"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      id: "favorite",
      header: "",
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <IconButton
            icon={Star}
            aria-label={lead.is_favorite ? "Unfavorite" : "Favorite"}
            variant="ghost"
            size="sm"
            className={cn(lead.is_favorite && "text-warning [&_svg]:fill-warning")}
            onClick={(event) => {
              event.stopPropagation();
              actions.onToggleFavorite(lead);
            }}
          />
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
    {
      id: "name",
      accessorFn: (lead) => lead.full_name,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Lead" />,
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <Link
            href={`/leads/${lead.id}`}
            className="flex items-center gap-3 hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            <Avatar size="sm" fallback={getInitials(lead.full_name)} />
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-body-sm font-medium text-foreground">{lead.full_name}</span>
              {lead.email && <span className="truncate text-caption text-muted-foreground">{lead.email}</span>}
            </div>
          </Link>
        );
      },
    },
    {
      id: "company",
      accessorFn: (lead) => lead.company_name ?? "",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Company" />,
      cell: ({ row }) => (
        <span className="text-body-sm text-foreground">{row.original.company_name || "—"}</span>
      ),
    },
    {
      id: "status",
      accessorFn: (lead) => lead.status,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      cell: ({ row }) => {
        const status = row.original.status as LeadStatus;
        return (
          <StatusBadge tone={STATUS_TONE[status] ?? "neutral"} pulse={status === "researching"}>
            {LEAD_STATUS_LABELS[status] ?? status}
          </StatusBadge>
        );
      },
    },
    {
      id: "owner",
      accessorFn: (lead) => lead.owner?.full_name ?? "",
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
      id: "tags",
      header: "Tags",
      cell: ({ row }) => {
        const tags = row.original.tags;
        if (tags.length === 0) return null;
        return (
          <div className="flex flex-wrap gap-1">
            {tags.slice(0, 2).map((tag) => (
              <Badge key={tag.id} variant="outline">
                {tag.name}
              </Badge>
            ))}
            {tags.length > 2 && <Badge variant="outline">+{tags.length - 2}</Badge>}
          </div>
        );
      },
      enableSorting: false,
    },
    {
      id: "lead_score",
      accessorFn: (lead) => lead.lead_score ?? -1,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Score" />,
      cell: ({ row }) => {
        const score = row.original.lead_score;
        return <span className="text-body-sm text-foreground">{score ?? "—"}</span>;
      },
    },
    {
      id: "created_at",
      accessorFn: (lead) => lead.created_at,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created" />,
      cell: ({ row }) => (
        <span className="text-body-sm text-muted-foreground">
          {formatDistanceToNow(new Date(row.original.created_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <DataTableRowActions>
            <DropdownMenuItem asChild>
              <Link href={`/leads/${lead.id}`}>
                <Eye className="size-4" />
                View
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => actions.onEdit(lead)}>
              <Pencil className="size-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => actions.onResearch(lead)}>
              <Sparkles className="size-4" />
              Research
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => actions.onToggleArchived(lead)}>
              {lead.is_archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {lead.is_archived ? "Restore" : "Archive"}
            </DropdownMenuItem>
            <DropdownMenuItem variant="danger" onSelect={() => actions.onDelete(lead)}>
              <Trash2 className="size-4" />
              Delete
            </DropdownMenuItem>
          </DataTableRowActions>
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
  ];
}
