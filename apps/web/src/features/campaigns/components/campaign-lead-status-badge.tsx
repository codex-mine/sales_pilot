import { StatusBadge } from "@/components/ui/status-badge";
import { CAMPAIGN_LEAD_STATUS_LABELS, type CampaignLeadStatus } from "../types";

const STATUS_TONE: Record<CampaignLeadStatus, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  enrolled: "info",
  in_progress: "primary",
  replied: "success",
  meeting_booked: "success",
  completed: "neutral",
  opted_out: "warning",
  bounced: "danger",
  paused: "warning",
};

export interface CampaignLeadStatusBadgeProps {
  status: string;
}

export function CampaignLeadStatusBadge({ status }: CampaignLeadStatusBadgeProps): React.ReactElement {
  const typedStatus = status as CampaignLeadStatus;
  return (
    <StatusBadge tone={STATUS_TONE[typedStatus] ?? "neutral"} pulse={status === "in_progress"}>
      {CAMPAIGN_LEAD_STATUS_LABELS[typedStatus] ?? status}
    </StatusBadge>
  );
}
