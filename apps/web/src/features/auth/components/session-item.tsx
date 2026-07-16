import { formatDistanceToNow } from "date-fns";
import { Laptop, LogOut, Monitor, Smartphone, Tablet } from "@/icons";
import { Badge } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/icon-button";
import type { SessionResponse } from "../types";

export interface SessionItemProps {
  session: SessionResponse;
  onRevoke: (sessionId: string) => void;
  isRevoking: boolean;
}

function deviceIcon(session: SessionResponse) {
  if (session.device?.is_mobile) return Smartphone;
  if (session.device?.is_tablet) return Tablet;
  if (session.device?.is_pc) return Monitor;
  return Laptop;
}

export function SessionItem({ session, onRevoke, isRevoking }: SessionItemProps): React.ReactElement {
  const DeviceIcon = deviceIcon(session);
  const deviceLabel = [session.device?.browser, session.device?.os].filter(Boolean).join(" on ") || "Unknown device";

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border p-4">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <DeviceIcon className="size-5" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="text-body-sm font-medium text-foreground">{deviceLabel}</span>
          {session.is_current && (
            <Badge variant="success" size="sm">
              This device
            </Badge>
          )}
        </div>
        <span className="text-caption text-muted-foreground">
          {session.ip_address ?? "Unknown IP"} · Active{" "}
          {formatDistanceToNow(new Date(session.last_active_at), { addSuffix: true })}
        </span>
      </div>
      {!session.is_current && (
        <IconButton
          icon={LogOut}
          aria-label="Revoke session"
          variant="ghost"
          size="sm"
          isLoading={isRevoking}
          onClick={() => onRevoke(session.id)}
        />
      )}
    </div>
  );
}
