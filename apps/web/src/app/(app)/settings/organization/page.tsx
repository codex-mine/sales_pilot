"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertTriangle, Building2, Users } from "@/icons";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PermissionGuard } from "@/components/guards";
import { EmailSenderSettingsPanel } from "@/features/email-sender/components/email-sender-settings-panel";
import { EditOrganizationDrawer } from "@/features/organizations/components/edit-organization-drawer";
import { InvitationList } from "@/features/organizations/components/invitation-list";
import { MembersTable } from "@/features/organizations/components/members-table";
import { OrganizationLogoUpload } from "@/features/organizations/components/organization-logo-upload";
import { OrganizationSettingsForm } from "@/features/organizations/components/organization-settings-form";
import { useDeleteOrganization } from "@/features/organizations/hooks/use-delete-organization";
import { useOrganizationDetail } from "@/features/organizations/hooks/use-organization-detail";
import { normalizeApiError } from "@/lib/api/errors";
import { useAuthStore } from "@/store/auth-store";

export default function OrganizationSettingsPage(): React.ReactElement {
  const { organization, isLoading, isError, errorMessage, refetch } = useOrganizationDetail();
  const { deleteOrganization, isDeleting } = useDeleteOrganization();
  const deleteConfirm = useConfirmDialog();
  const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
  const router = useRouter();

  async function handleDeleteOrganization(): Promise<void> {
    try {
      await deleteOrganization();
      // A client-only `clear()` isn't enough here: the httpOnly access_token
      // cookie is still valid (deleting an org doesn't revoke sessions), and
      // the Next.js middleware checks that cookie's *presence* to gate
      // /login — so it would just bounce straight back to /dashboard.
      // `logout()` calls the real endpoint, which revokes the session and
      // clears the cookie server-side.
      await useAuthStore.getState().logout();
      router.replace("/login");
    } catch (error) {
      deleteConfirm.close();
      // A toast-worthy message; the guard below also re-fetches on next mount.
      window.alert(normalizeApiError(error).message);
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !organization) {
    return (
      <ErrorState
        title="Couldn't load organization"
        description={errorMessage ?? undefined}
        onRetry={refetch}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
          <div className="flex items-center gap-4">
            <OrganizationLogoUpload logoUrl={organization.logo_url} organizationName={organization.name} />
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <div className="flex items-center gap-2">
              <h2 className="text-heading-5 font-semibold text-foreground">{organization.name}</h2>
              <Badge variant={organization.is_active ? "success" : "danger"}>
                {organization.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <p className="text-body-sm text-muted-foreground">
              {organization.slug} · {organization.member_count}{" "}
              {organization.member_count === 1 ? "member" : "members"}
            </p>
          </div>
          <PermissionGuard permission="organizations.update" fallback={<></>}>
            <EditOrganizationDrawer
              organization={organization}
              open={isEditDrawerOpen}
              onOpenChange={setIsEditDrawerOpen}
            />
          </PermissionGuard>
        </CardContent>
      </Card>

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
          <PermissionGuard permission="campaigns.manage" fallback={<></>}>
            <TabsTrigger value="email-sender">Email Sender</TabsTrigger>
          </PermissionGuard>
          <PermissionGuard permission="organizations.delete" fallback={<></>}>
            <TabsTrigger value="danger">Danger zone</TabsTrigger>
          </PermissionGuard>
        </TabsList>

        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>Organization profile</CardTitle>
              <CardDescription>Basic information visible to your team.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Name" value={organization.name} />
                <Field label="URL slug" value={organization.slug} />
                <Field label="Website" value={organization.website} />
                <Field label="Contact email" value={organization.email} />
                <Field label="Phone" value={organization.phone} />
                <Field label="Industry" value={organization.industry} />
                <Field label="Country" value={organization.country} />
                <Field label="Company size" value={organization.company_size} />
              </dl>
              {organization.description && (
                <p className="mt-4 text-body-sm text-muted-foreground">{organization.description}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <PermissionGuard
            permission="organizations.update"
            fallback={
              <p className="text-body-sm text-muted-foreground">
                You don&apos;t have permission to change organization settings.
              </p>
            }
          >
            <OrganizationSettingsForm organization={organization} />
          </PermissionGuard>
        </TabsContent>

        <TabsContent value="members">
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="size-4" />
                  Members
                </CardTitle>
                <CardDescription>Everyone with access to this workspace.</CardDescription>
              </CardHeader>
              <CardContent>
                <PermissionGuard
                  permission="users.read"
                  fallback={
                    <p className="text-body-sm text-muted-foreground">
                      You don&apos;t have permission to view members.
                    </p>
                  }
                >
                  <MembersTable />
                </PermissionGuard>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Pending invitations</CardTitle>
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
        </TabsContent>

        <PermissionGuard permission="campaigns.manage" fallback={<></>}>
          <TabsContent value="email-sender">
            <EmailSenderSettingsPanel />
          </TabsContent>
        </PermissionGuard>

        <PermissionGuard permission="organizations.delete" fallback={<></>}>
          <TabsContent value="danger">
            <Card className="border-danger/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-danger">
                  <AlertTriangle className="size-4" />
                  Delete organization
                </CardTitle>
                <CardDescription>
                  Permanently deletes this workspace and signs everyone out. This cannot be undone.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="danger" onClick={deleteConfirm.open}>
                  <Building2 className="size-4" />
                  Delete this organization
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </PermissionGuard>
      </Tabs>

      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this organization?"
        description={`This permanently deletes "${organization.name}" and signs out every member, including you. This action cannot be undone.`}
        confirmLabel="Delete organization"
        isConfirming={isDeleting}
        onConfirm={handleDeleteOrganization}
      />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }): React.ReactElement {
  return (
    <div>
      <dt className="text-caption text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-body-sm text-foreground">{value || "—"}</dd>
    </div>
  );
}
