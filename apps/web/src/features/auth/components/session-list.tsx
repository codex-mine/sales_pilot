"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Monitor } from "@/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/store/auth-store";
import { useSession } from "../hooks/use-session";
import { SessionItem } from "./session-item";

/** Backs Settings → Security → Active sessions. Wired to `GET/DELETE /auth/sessions`, plus `POST /auth/logout-all`. */
export function SessionList(): React.ReactElement {
  const { sessions, isLoading, isError, errorMessage, refetch, revokeSession, isRevoking } = useSession();
  const logoutAll = useAuthStore((state) => state.logoutAll);

  const logoutAllMutation = useMutation({
    mutationFn: logoutAll,
    onSuccess: () => toast.success("Logged out of all devices."),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  if (sessions.length === 0) {
    return <EmptyState icon={Monitor} title="No active sessions" description="You're not signed in anywhere." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        {sessions.map((session) => (
          <SessionItem
            key={session.id}
            session={session}
            onRevoke={revokeSession}
            isRevoking={isRevoking}
          />
        ))}
      </div>
      {sessions.length > 1 && (
        <Button
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => logoutAllMutation.mutate()}
          isLoading={logoutAllMutation.isPending}
        >
          Log out of all devices
        </Button>
      )}
    </div>
  );
}
