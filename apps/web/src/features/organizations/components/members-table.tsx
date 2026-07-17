"use client";

import { DataTable } from "@/components/data-table";
import { ErrorState } from "@/components/ui/error-state";
import { useOrganizationMembers } from "../hooks/use-organization-members";
import { membersTableColumns } from "./members-table-columns";

/** Search/sort/pagination are handled client-side by the shared `DataTable` — see `useOrganizationMembers`'s docstring for why. */
export function MembersTable(): React.ReactElement {
  const { members, isLoading, isError, errorMessage } = useOrganizationMembers();

  if (isError) {
    return <ErrorState title="Couldn't load members" description={errorMessage ?? undefined} />;
  }

  return (
    <DataTable
      columns={membersTableColumns}
      data={members}
      isLoading={isLoading}
      searchPlaceholder="Search members..."
      emptyTitle="No members yet"
      emptyDescription="Invite teammates to see them listed here."
    />
  );
}
