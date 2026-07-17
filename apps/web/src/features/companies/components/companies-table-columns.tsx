"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { DataTableColumnHeader, DataTableRowActions } from "@/components/data-table";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/ui/status-badge";
import { Archive, ArchiveRestore, Building2, Eye, Pencil, Trash2 } from "@/icons";
import { getInitials } from "@/lib/utils";
import { getMediaUrl } from "@/lib/api/client";
import { COMPANY_STATUS_LABELS, type CompanyResponse, type CompanyStatus } from "../types";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  prospect: "info",
  active: "primary",
  customer: "success",
  partner: "primary",
  churned: "danger",
  inactive: "neutral",
};

export interface CompaniesTableActions {
  onToggleArchived: (company: CompanyResponse) => void;
  onEdit: (company: CompanyResponse) => void;
  onDelete: (company: CompanyResponse) => void;
}

export function buildCompaniesTableColumns(actions: CompaniesTableActions): ColumnDef<CompanyResponse>[] {
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
      id: "name",
      accessorFn: (company) => company.name,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Company" />,
      cell: ({ row }) => {
        const company = row.original;
        return (
          <Link
            href={`/companies/${company.id}`}
            className="flex items-center gap-3 hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            <Avatar
              size="sm"
              src={getMediaUrl(company.logo_url)}
              fallback={company.logo_url ? <Building2 className="size-4" /> : getInitials(company.name)}
            />
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-body-sm font-medium text-foreground">{company.name}</span>
              {company.website && (
                <span className="truncate text-caption text-muted-foreground">{company.domain ?? company.website}</span>
              )}
            </div>
          </Link>
        );
      },
    },
    {
      id: "industry",
      accessorFn: (company) => company.industry ?? "",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Industry" />,
      cell: ({ row }) => <span className="text-body-sm text-foreground">{row.original.industry || "—"}</span>,
    },
    {
      id: "status",
      accessorFn: (company) => company.status,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      cell: ({ row }) => {
        const status = row.original.status as CompanyStatus;
        return (
          <StatusBadge tone={STATUS_TONE[status] ?? "neutral"}>
            {COMPANY_STATUS_LABELS[status] ?? status}
          </StatusBadge>
        );
      },
    },
    {
      id: "owner",
      accessorFn: (company) => company.owner?.full_name ?? "",
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
      id: "employee_count",
      accessorFn: (company) => company.employee_count ?? -1,
      header: ({ column }) => <DataTableColumnHeader column={column} title="Employees" />,
      cell: ({ row }) => (
        <span className="text-body-sm text-foreground">{row.original.employee_count ?? "—"}</span>
      ),
    },
    {
      id: "created_at",
      accessorFn: (company) => company.created_at,
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
        const company = row.original;
        return (
          <DataTableRowActions>
            <DropdownMenuItem asChild>
              <Link href={`/companies/${company.id}`}>
                <Eye className="size-4" />
                View
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => actions.onEdit(company)}>
              <Pencil className="size-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => actions.onToggleArchived(company)}>
              {company.is_archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {company.is_archived ? "Restore" : "Archive"}
            </DropdownMenuItem>
            <DropdownMenuItem variant="danger" onSelect={() => actions.onDelete(company)}>
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
