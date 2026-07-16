"use client";

import { formatDistanceToNow } from "date-fns";
import { Mail, X } from "@/icons";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { IconButton } from "@/components/ui/icon-button";
import { Skeleton } from "@/components/ui/skeleton";
import { useInvitations } from "../hooks/use-invitations";
import { useRoles } from "../hooks/use-roles";
import { InviteMemberDialog } from "./invite-member-dialog";

/** Backs Settings → Organization → Pending invitations. Wired to `GET/POST/DELETE /organizations/invitations`. */
export function InvitationList(): React.ReactElement {
  const { invitations, isLoading, isError, errorMessage, revokeInvitation, isRevoking } =
    useInvitations();
  const { roles } = useRoles();

  const roleName = (roleId: string): string =>
    roles.find((role) => role.id === roleId)?.name ?? "member";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-body-md font-semibold text-foreground">Pending invitations</h3>
          <p className="text-body-sm text-muted-foreground">
            People who&apos;ve been invited but haven&apos;t joined yet.
          </p>
        </div>
        <InviteMemberDialog />
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 2 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState description={errorMessage ?? undefined} />
      ) : invitations.length === 0 ? (
        <EmptyState icon={Mail} title="No pending invitations" description="Invite a teammate to get started." />
      ) : (
        <div className="flex flex-col gap-3">
          {invitations.map((invitation) => (
            <div
              key={invitation.id}
              className="flex items-center gap-4 rounded-lg border border-border p-4"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <Mail className="size-4" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate text-body-sm font-medium text-foreground">
                  {invitation.email}
                </span>
                <span className="text-caption text-muted-foreground">
                  Invited as {roleName(invitation.role_id)} · Expires{" "}
                  {formatDistanceToNow(new Date(invitation.expires_at), { addSuffix: true })}
                </span>
              </div>
              <Badge variant="soft" size="sm">
                {invitation.status}
              </Badge>
              <IconButton
                icon={X}
                aria-label="Revoke invitation"
                variant="ghost"
                size="sm"
                isLoading={isRevoking}
                onClick={() => revokeInvitation(invitation.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
