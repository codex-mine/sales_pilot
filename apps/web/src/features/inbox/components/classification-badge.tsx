import { StatusBadge } from "@/components/ui/status-badge";
import { REPLY_CLASSIFICATION_LABELS, type ReplyClassification } from "../types";

const CLASSIFICATION_TONE: Record<ReplyClassification, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  interested: "success",
  meeting_requested: "success",
  not_interested: "neutral",
  needs_follow_up: "warning",
  referral: "info",
  out_of_office: "neutral",
  spam: "danger",
  unsubscribe_request: "danger",
  unknown: "neutral",
};

export interface ClassificationBadgeProps {
  classification: string | null | undefined;
  className?: string;
}

export function ClassificationBadge({ classification, className }: ClassificationBadgeProps): React.ReactElement | null {
  if (!classification) return null;
  const key = classification as ReplyClassification;
  return (
    <StatusBadge tone={CLASSIFICATION_TONE[key] ?? "neutral"} className={className}>
      {REPLY_CLASSIFICATION_LABELS[key] ?? classification}
    </StatusBadge>
  );
}
