"use client";

import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FileText, Pencil, Play, Trash2 } from "@/icons";
import { useDeleteReport, useRunReport } from "../hooks/use-report-mutations";
import { useReports } from "../hooks/use-reports";
import { REPORT_TYPE_LABELS, type ReportResponse } from "../types";

export interface ReportsTableProps {
  onEdit: (report: ReportResponse) => void;
  onCreate: () => void;
}

export function ReportsTable({ onEdit, onCreate }: ReportsTableProps): React.ReactElement {
  const { reports, isLoading } = useReports();
  const { runReport, isRunning } = useRunReport();
  const { deleteReport, isDeleting } = useDeleteReport();
  const [pendingDelete, setPendingDelete] = useState<ReportResponse | null>(null);
  const deleteConfirm = useConfirmDialog();

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDelete) return;
    await deleteReport(pendingDelete.id);
    deleteConfirm.close();
    setPendingDelete(null);
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No saved reports yet"
        description="Create a report to save a filtered view of your pipeline, campaigns, or AI usage — optionally delivered on a schedule."
        action={
          <Button size="sm" onClick={onCreate}>
            Create report
          </Button>
        }
      />
    );
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Data source</TableHead>
            <TableHead>Schedule</TableHead>
            <TableHead>Last run</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {reports.map((report) => (
            <TableRow key={report.id}>
              <TableCell>
                <span className="text-body-sm font-medium text-foreground">{report.name}</span>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{REPORT_TYPE_LABELS[report.report_type as keyof typeof REPORT_TYPE_LABELS] ?? report.report_type}</Badge>
              </TableCell>
              <TableCell>
                <span className="text-body-sm text-muted-foreground">
                  {report.is_scheduled ? `${report.schedule_cron}` : "Manual"}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-body-sm text-muted-foreground">
                  {report.last_run_at ? formatDistanceToNow(new Date(report.last_run_at), { addSuffix: true }) : "Never"}
                </span>
              </TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1">
                  <Button variant="ghost" size="sm" onClick={() => void runReport(report.id)} isLoading={isRunning}>
                    <Play className="size-4" />
                    Run
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => onEdit(report)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    onClick={() => {
                      setPendingDelete(report);
                      deleteConfirm.open();
                    }}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this report?"
        description={`This permanently deletes "${pendingDelete?.name ?? "this report"}". This cannot be undone.`}
        confirmLabel="Delete report"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
