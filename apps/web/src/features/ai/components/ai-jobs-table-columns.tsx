"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { DataTableColumnHeader } from "@/components/data-table";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatCurrency } from "@/lib/utils";
import { LLM_PROVIDER_LABELS, type AIJobListItemResponse, type AIJobStatus, type LLMProvider } from "../types";

const STATUS_TONE: Record<AIJobStatus, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  pending: "neutral",
  running: "info",
  retrying: "warning",
  completed: "success",
  failed: "danger",
  cancelled: "neutral",
};

const STATUS_LABELS: Record<AIJobStatus, string> = {
  pending: "Pending",
  running: "Running",
  retrying: "Retrying",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const aiJobsTableColumns: ColumnDef<AIJobListItemResponse>[] = [
  {
    accessorKey: "job_type",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Job type" />,
    cell: ({ row }) => <span className="font-medium text-foreground">{row.original.job_type}</span>,
  },
  {
    accessorKey: "entity_type",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Entity" />,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.entity_type ? `${row.original.entity_type}` : "—"}
      </span>
    ),
    enableSorting: false,
  },
  {
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => (
      <StatusBadge tone={STATUS_TONE[row.original.status]} pulse={row.original.status === "running"}>
        {STATUS_LABELS[row.original.status]}
      </StatusBadge>
    ),
  },
  {
    accessorKey: "model_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Provider / model" />,
    cell: ({ row }) => (
      <span className="text-body-sm text-muted-foreground">
        {row.original.provider ? (LLM_PROVIDER_LABELS[row.original.provider as LLMProvider] ?? row.original.provider) : "—"}
        {row.original.model_name ? ` · ${row.original.model_name}` : ""}
      </span>
    ),
    enableSorting: false,
  },
  {
    accessorKey: "total_tokens",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Tokens" />,
    cell: ({ row }) => <span>{row.original.total_tokens?.toLocaleString() ?? "—"}</span>,
  },
  {
    accessorKey: "cost_usd",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Cost" />,
    cell: ({ row }) => <span>{row.original.cost_usd != null ? formatCurrency(row.original.cost_usd) : "—"}</span>,
  },
  {
    accessorKey: "latency_ms",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Latency" />,
    cell: ({ row }) => <span>{row.original.latency_ms != null ? `${row.original.latency_ms}ms` : "—"}</span>,
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Started" />,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {formatDistanceToNow(new Date(row.original.created_at), { addSuffix: true })}
      </span>
    ),
  },
];
