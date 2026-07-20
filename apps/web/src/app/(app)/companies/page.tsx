"use client";

import { useState } from "react";
import { PermissionGuard } from "@/components/guards";
import { PageLayout } from "@/components/layout/page-layout";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Plus } from "@/icons";
import { CompaniesTable } from "@/features/companies/components/companies-table";
import { CompanyFormDrawer } from "@/features/companies/components/company-form-drawer";
import type { CompanyResponse } from "@/features/companies/types";

function CompaniesPageContent(): React.ReactElement {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<CompanyResponse | undefined>(undefined);

  return (
    <PageLayout>
      <PageHeader
        title="Companies"
        description="Manage the businesses you sell to — profiles, employees, and activity in one place."
        actions={
          <Button
            onClick={() => {
              setEditingCompany(undefined);
              setDrawerOpen(true);
            }}
          >
            <Plus className="size-4" />
            Create company
          </Button>
        }
      />

      <PermissionGuard permission="companies.read">
        <CompaniesTable
          onEditCompany={(company) => {
            setEditingCompany(company);
            setDrawerOpen(true);
          }}
          onCreateCompany={() => {
            setEditingCompany(undefined);
            setDrawerOpen(true);
          }}
        />
      </PermissionGuard>

      <CompanyFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} company={editingCompany} />
    </PageLayout>
  );
}

export default function CompaniesPage(): React.ReactElement {
  return <CompaniesPageContent />;
}
