"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { DataTableRowActions } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/ui/status-badge";
import { Pencil, Sparkles, Trash2 } from "@/icons";
import {
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_LABELS,
  type EmailTemplateResponse,
  type EmailTemplateType,
  type EmailTone,
} from "../types";

export interface EmailTemplatesTableActions {
  onEdit: (template: EmailTemplateResponse) => void;
  onDelete: (template: EmailTemplateResponse) => void;
}

export function buildEmailTemplatesTableColumns(
  actions: EmailTemplatesTableActions,
): ColumnDef<EmailTemplateResponse>[] {
  return [
    {
      id: "name",
      accessorFn: (template) => template.name,
      header: "Name",
      cell: ({ row }) => {
        const template = row.original;
        return (
          <div className="flex items-center gap-2">
            <span className="font-medium text-foreground">{template.name}</span>
            {template.is_ai_generated && (
              <Badge variant="soft">
                <Sparkles className="size-3" />
                AI
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      id: "template_type",
      accessorFn: (template) => template.template_type,
      header: "Type",
      cell: ({ row }) => {
        const type = row.original.template_type as EmailTemplateType;
        return <span className="text-body-sm text-foreground">{EMAIL_TEMPLATE_TYPE_LABELS[type] ?? type}</span>;
      },
    },
    {
      id: "tone",
      accessorFn: (template) => template.tone ?? "",
      header: "Tone",
      cell: ({ row }) => {
        const tone = row.original.tone as EmailTone | null;
        return <span className="text-body-sm text-muted-foreground">{tone ? EMAIL_TONE_LABELS[tone] ?? tone : "—"}</span>;
      },
    },
    {
      id: "subject",
      accessorFn: (template) => template.subject,
      header: "Subject",
      cell: ({ row }) => (
        <span className="block max-w-64 truncate text-body-sm text-foreground">{row.original.subject}</span>
      ),
      enableSorting: false,
    },
    {
      id: "usage",
      header: "Usage",
      cell: ({ row }) => {
        const t = row.original;
        return (
          <span className="text-body-sm text-muted-foreground">
            {t.total_sent} sent · {t.total_opened} opened · {t.total_replied} replied
          </span>
        );
      },
      enableSorting: false,
    },
    {
      id: "is_active",
      accessorFn: (template) => template.is_active,
      header: "Status",
      cell: ({ row }) => (
        <StatusBadge tone={row.original.is_active ? "success" : "neutral"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </StatusBadge>
      ),
    },
    {
      id: "updated_at",
      accessorFn: (template) => template.updated_at,
      header: "Updated",
      cell: ({ row }) => (
        <span className="text-body-sm text-muted-foreground">
          {formatDistanceToNow(new Date(row.original.updated_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const template = row.original;
        return (
          <DataTableRowActions>
            <DropdownMenuItem onSelect={() => actions.onEdit(template)}>
              <Pencil className="size-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem variant="danger" onSelect={() => actions.onDelete(template)}>
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
