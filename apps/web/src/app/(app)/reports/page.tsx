"use client";

import { useState } from "react";
import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Plus } from "@/icons";
import { ReportFormDialog } from "@/features/dashboard/components/report-form-dialog";
import { ReportsTable } from "@/features/dashboard/components/reports-table";
import type { ReportResponse } from "@/features/dashboard/types";

function ReportsPageContent(): React.ReactElement {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingReport, setEditingReport] = useState<ReportResponse | undefined>(undefined);

  return (
    <PageLayout>
      <PageHeader
        title="Reports"
        description="Saved views of your pipeline, campaigns, and AI usage — run on demand or deliver on a schedule."
        actions={
          <Button
            onClick={() => {
              setEditingReport(undefined);
              setDialogOpen(true);
            }}
          >
            <Plus className="size-4" />
            Create report
          </Button>
        }
      />

      <PermissionGuard permission="reports.read">
        <ReportsTable
          onEdit={(report) => {
            setEditingReport(report);
            setDialogOpen(true);
          }}
          onCreate={() => {
            setEditingReport(undefined);
            setDialogOpen(true);
          }}
        />
      </PermissionGuard>

      <ReportFormDialog open={dialogOpen} onOpenChange={setDialogOpen} report={editingReport} />
    </PageLayout>
  );
}

export default function ReportsPage(): React.ReactElement {
  return <ReportsPageContent />;
}
