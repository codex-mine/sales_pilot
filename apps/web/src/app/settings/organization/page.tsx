"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PermissionGuard } from "@/components/guards";
import { InvitationList } from "@/features/organizations/components/invitation-list";
import { useOrganization } from "@/features/organizations/hooks/use-organization";

export default function OrganizationSettingsPage(): React.ReactElement {
  const { organization } = useOrganization();

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>General information about your organization.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-caption text-muted-foreground">Name</dt>
              <dd className="mt-1 text-body-sm text-foreground">{organization?.name}</dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">URL slug</dt>
              <dd className="mt-1 text-body-sm text-foreground">{organization?.slug}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>Invite teammates and manage pending invitations.</CardDescription>
        </CardHeader>
        <CardContent>
          <PermissionGuard
            permission="users.read"
            fallback={
              <p className="text-body-sm text-muted-foreground">
                You don&apos;t have permission to manage members. Contact your workspace owner or admin.
              </p>
            }
          >
            <InvitationList />
          </PermissionGuard>
        </CardContent>
      </Card>
    </div>
  );
}
