import { StatusBadge } from "@/components/ui/status-badge";
import { CAMPAIGN_STATUS_LABELS, type CampaignStatus } from "../types";

const STATUS_TONE: Record<CampaignStatus, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  draft: "neutral",
  active: "success",
  paused: "warning",
  completed: "primary",
  archived: "neutral",
};

export interface CampaignStatusBadgeProps {
  status: string;
}

export function CampaignStatusBadge({ status }: CampaignStatusBadgeProps): React.ReactElement {
  const typedStatus = status as CampaignStatus;
  return (
    <StatusBadge tone={STATUS_TONE[typedStatus] ?? "neutral"} pulse={status === "active"}>
      {CAMPAIGN_STATUS_LABELS[typedStatus] ?? status}
    </StatusBadge>
  );
}
