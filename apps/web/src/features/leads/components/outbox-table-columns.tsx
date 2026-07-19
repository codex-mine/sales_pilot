"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { DataTableRowActions } from "@/components/data-table";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/ui/status-badge";
import { Eye, RefreshCw, Send, X } from "@/icons";
import type { OutboxEmailResponse } from "../types";

export interface OutboxTableActions {
  onSend: (email: OutboxEmailResponse) => void;
  onCancel: (email: OutboxEmailResponse) => void;
  onPreview: (email: OutboxEmailResponse) => void;
}

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  draft: "neutral",
  scheduled: "info",
  sending: "info",
  sent: "success",
  delivered: "success",
  opened: "success",
  clicked: "success",
  bounced: "danger",
  failed: "danger",
  spam: "danger",
};

export function buildOutboxTableColumns(actions: OutboxTableActions): ColumnDef<OutboxEmailResponse>[] {
  return [
    {
      id: "lead",
      accessorFn: (email) => email.lead_full_name ?? "",
      header: "Lead",
      cell: ({ row }) => {
        const email = row.original;
        return (
          <Link href={`/leads/${email.lead_id}`} className="flex flex-col hover:underline" onClick={(e) => e.stopPropagation()}>
            <span className="text-body-sm font-medium text-foreground">{email.lead_full_name || "—"}</span>
            {email.lead_company_name && (
              <span className="text-caption text-muted-foreground">{email.lead_company_name}</span>
            )}
          </Link>
        );
      },
    },
    {
      id: "subject",
      accessorFn: (email) => email.subject,
      header: "Subject",
      cell: ({ row }) => <span className="block max-w-72 truncate text-body-sm text-foreground">{row.original.subject}</span>,
      enableSorting: false,
    },
    {
      id: "current_status",
      accessorFn: (email) => email.current_status,
      header: "Status",
      cell: ({ row }) => {
        const email = row.original;
        return (
          <div className="flex flex-col gap-0.5">
            <StatusBadge tone={STATUS_TONE[email.current_status] ?? "neutral"} pulse={email.current_status === "sending"}>
              {email.current_status}
            </StatusBadge>
            {email.current_status === "failed" && email.send_error && (
              <span className="max-w-56 truncate text-caption text-danger" title={email.send_error}>
                {email.send_error}
              </span>
            )}
            {(email.current_status === "bounced" || email.current_status === "spam") && email.bounce_reason && (
              <span className="max-w-56 truncate text-caption text-danger" title={email.bounce_reason}>
                {email.bounce_reason}
              </span>
            )}
          </div>
        );
      },
    },
    {
      id: "timing",
      header: "Timing",
      cell: ({ row }) => {
        const email = row.original;
        if (email.current_status === "scheduled" && email.scheduled_at) {
          return <span className="text-body-sm text-muted-foreground">{new Date(email.scheduled_at).toLocaleString()}</span>;
        }
        if (email.sent_at) {
          return (
            <span className="text-body-sm text-muted-foreground">
              {formatDistanceToNow(new Date(email.sent_at), { addSuffix: true })}
            </span>
          );
        }
        return (
          <span className="text-body-sm text-muted-foreground">
            {formatDistanceToNow(new Date(email.created_at), { addSuffix: true })}
          </span>
        );
      },
      enableSorting: false,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const email = row.original;
        const canSend = email.current_status === "draft" || email.current_status === "failed";
        return (
          <DataTableRowActions>
            <DropdownMenuItem onSelect={() => actions.onPreview(email)}>
              <Eye className="size-4" />
              Preview
            </DropdownMenuItem>
            {canSend && (
              <DropdownMenuItem onSelect={() => actions.onSend(email)}>
                {email.current_status === "failed" ? <RefreshCw className="size-4" /> : <Send className="size-4" />}
                {email.current_status === "failed" ? "Retry" : "Send Now"}
              </DropdownMenuItem>
            )}
            {email.current_status === "scheduled" && (
              <DropdownMenuItem variant="danger" onSelect={() => actions.onCancel(email)}>
                <X className="size-4" />
                Cancel
              </DropdownMenuItem>
            )}
          </DataTableRowActions>
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
  ];
}
