"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthGuard, PermissionGuard } from "@/components/guards";
import { AppShell } from "@/components/layouts/app-shell";
import { PageLayout } from "@/components/layout/page-layout";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Plus, Upload } from "@/icons";
import { LeadFormDrawer } from "@/features/leads/components/lead-form-drawer";
import { LeadsTable } from "@/features/leads/components/leads-table";
import type { LeadResponse } from "@/features/leads/types";

function LeadsPageContent(): React.ReactElement {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<LeadResponse | undefined>(undefined);

  return (
    <PageLayout>
      <PageHeader
        title="Leads"
        description="Manage prospects, track pipeline status, and grow your book of business."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link href="/leads/import">
                <Upload className="size-4" />
                Import CSV
              </Link>
            </Button>
            <Button
              onClick={() => {
                setEditingLead(undefined);
                setDrawerOpen(true);
              }}
            >
              <Plus className="size-4" />
              Create lead
            </Button>
          </>
        }
      />

      <PermissionGuard permission="leads.read">
        <LeadsTable
          onEditLead={(lead) => {
            setEditingLead(lead);
            setDrawerOpen(true);
          }}
          onCreateLead={() => {
            setEditingLead(undefined);
            setDrawerOpen(true);
          }}
        />
      </PermissionGuard>

      <LeadFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} lead={editingLead} />
    </PageLayout>
  );
}

export default function LeadsPage(): React.ReactElement {
  return (
    <AuthGuard>
      <AppShell>
        <LeadsPageContent />
      </AppShell>
    </AuthGuard>
  );
}
