import { StatusBadge } from "@/components/ui/status-badge";
import { MEETING_STATUS_LABELS, type MeetingStatus } from "../types";

const STATUS_TONE: Record<MeetingStatus, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  proposed: "info",
  confirmed: "success",
  rescheduled: "warning",
  cancelled: "danger",
  completed: "primary",
  no_show: "danger",
};

export function MeetingStatusBadge({ status }: { status: string }): React.ReactElement {
  const key = status as MeetingStatus;
  return (
    <StatusBadge tone={STATUS_TONE[key] ?? "neutral"}>{MEETING_STATUS_LABELS[key] ?? status}</StatusBadge>
  );
}
