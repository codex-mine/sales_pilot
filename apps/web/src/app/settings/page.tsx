"use client";

import { CheckCircle2, MailWarning } from "@/icons";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { useOrganization } from "@/features/organizations/hooks/use-organization";
import { getInitials } from "@/lib/utils";

export default function ProfileSettingsPage(): React.ReactElement {
  const user = useCurrentUser();
  const { organization } = useOrganization();

  if (!user) return <></>;

  return (
    <div className="flex flex-col gap-6">
      {!user.email_verified && (
        <Alert variant="warning" icon={MailWarning}>
          <AlertDescription>
            Your email address isn&apos;t verified yet. Check your inbox for a verification link.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <Avatar size="lg" src={user.avatar_url} fallback={getInitials(user.full_name)} />
            <div>
              <p className="text-body-lg font-medium text-foreground">{user.full_name}</p>
              <p className="text-body-sm text-muted-foreground">{user.email}</p>
            </div>
          </div>

          <Separator />

          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-caption text-muted-foreground">Role</dt>
              <dd className="mt-1">
                <Badge variant="soft">{user.role ?? "—"}</Badge>
              </dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">Email status</dt>
              <dd className="mt-1 flex items-center gap-1.5 text-body-sm">
                {user.email_verified ? (
                  <>
                    <CheckCircle2 className="size-3.5 text-success" />
                    Verified
                  </>
                ) : (
                  <>
                    <MailWarning className="size-3.5 text-warning" />
                    Not verified
                  </>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">Workspace</dt>
              <dd className="mt-1 text-body-sm text-foreground">{organization?.name}</dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">Account status</dt>
              <dd className="mt-1 text-body-sm capitalize text-foreground">
                {user.status.replace(/_/g, " ")}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
