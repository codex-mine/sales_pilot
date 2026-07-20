"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { DataTableColumnHeader, DataTableRowActions } from "@/components/data-table";
import { Avatar } from "@/components/ui/avatar";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Archive, Eye, Pause, Pencil, Play, Trash2 } from "@/icons";
import { getInitials } from "@/lib/utils";
import type { CampaignResponse } from "../types";
import { CampaignStatusBadge } from "./campaign-status-badge";

export interface CampaignsTableActions {
  onEdit: (campaign: CampaignResponse) => void;
  onActivate: (campaign: CampaignResponse) => void;
  onPause: (campaign: CampaignResponse) => void;
  onArchive: (campaign: CampaignResponse) => void;
  onDelete: (campaign: CampaignResponse) => void;
}

export function buildCampaignsTableColumns(actions: CampaignsTableActions): ColumnDef<CampaignResponse>[] {
  return [
    {
      id: "name",
      accessorFn: (campaign) => campaign.name,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Campaign" />,
      cell: ({ row }) => {
        const campaign = row.original;
        return (
          <Link
            href={`/campaigns/${campaign.id}`}
            className="flex flex-col gap-0.5 hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            <span className="truncate text-body-sm font-medium text-foreground">{campaign.name}</span>
            {campaign.goal && <span className="truncate text-caption text-muted-foreground">{campaign.goal}</span>}
          </Link>
        );
      },
    },
    {
      id: "status",
      accessorFn: (campaign) => campaign.status,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      cell: ({ row }) => <CampaignStatusBadge status={row.original.status} />,
    },
    {
      id: "enrolled_count",
      accessorFn: (campaign) => campaign.enrolled_count,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Enrolled" />,
      cell: ({ row }) => <span className="text-body-sm text-foreground">{row.original.enrolled_count}</span>,
    },
    {
      id: "owner",
      accessorFn: (campaign) => campaign.owner?.full_name ?? "",
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
      id: "requires_approval",
      accessorFn: (campaign) => campaign.requires_approval,
      header: "Sending",
      cell: ({ row }) => (
        <span className="text-body-sm text-muted-foreground">
          {row.original.requires_approval ? "Approval required" : "Full automation"}
        </span>
      ),
      enableSorting: false,
    },
    {
      id: "created_at",
      accessorFn: (campaign) => campaign.created_at,
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
        const campaign = row.original;
        return (
          <DataTableRowActions>
            <DropdownMenuItem asChild>
              <Link href={`/campaigns/${campaign.id}`}>
                <Eye className="size-4" />
                View
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => actions.onEdit(campaign)}>
              <Pencil className="size-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {(campaign.status === "draft" || campaign.status === "paused") && (
              <DropdownMenuItem onSelect={() => actions.onActivate(campaign)}>
                <Play className="size-4" />
                Activate
              </DropdownMenuItem>
            )}
            {campaign.status === "active" && (
              <DropdownMenuItem onSelect={() => actions.onPause(campaign)}>
                <Pause className="size-4" />
                Pause
              </DropdownMenuItem>
            )}
            {campaign.status !== "archived" && (
              <DropdownMenuItem onSelect={() => actions.onArchive(campaign)}>
                <Archive className="size-4" />
                Archive
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="danger"
              onSelect={() => actions.onDelete(campaign)}
              disabled={campaign.status === "active"}
            >
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
