"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, Mail, MessageSquare, Target } from "@/icons";
import { useCampaignDashboard } from "../hooks/use-campaign-dashboard";
import type { CampaignFunnelCounts } from "../types";

const FUNNEL_STAGES: { key: keyof CampaignFunnelCounts; label: string; color: string }[] = [
  { key: "enrolled", label: "Enrolled", color: "hsl(var(--info))" },
  { key: "in_progress", label: "In progress", color: "hsl(var(--primary))" },
  { key: "replied", label: "Replied", color: "hsl(var(--success))" },
  { key: "meeting_booked", label: "Meeting booked", color: "hsl(var(--success))" },
  { key: "completed", label: "Completed", color: "hsl(var(--muted-foreground))" },
  { key: "opted_out", label: "Opted out", color: "hsl(var(--warning))" },
  { key: "bounced", label: "Bounced", color: "hsl(var(--danger))" },
];

function StatTile({
  icon: Icon, label, value,
}: {
  icon: typeof Mail;
  label: string;
  value: string;
}): React.ReactElement {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border p-4">
      <div className="flex items-center gap-1.5 text-caption text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </div>
      <span className="text-heading-4 font-semibold text-foreground">{value}</span>
    </div>
  );
}

export interface CampaignDashboardPanelProps {
  campaignId: string;
}

export function CampaignDashboardPanel({ campaignId }: CampaignDashboardPanelProps): React.ReactElement {
  const { dashboard, isLoading, isError, errorMessage, refetch } = useCampaignDashboard(campaignId);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (isError || !dashboard) {
    return <ErrorState title="Couldn't load dashboard" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  const chartData = FUNNEL_STAGES.map((stage) => ({
    stage: stage.label,
    count: dashboard.funnel[stage.key],
    color: stage.color,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <StatTile icon={Target} label="Total enrolled" value={String(dashboard.total_enrolled)} />
        <StatTile icon={Mail} label="Emails sent today" value={String(dashboard.emails_sent)} />
        <StatTile icon={MessageSquare} label="Reply rate" value={`${dashboard.reply_rate.toFixed(1)}%`} />
        <StatTile icon={BarChart3} label="Meeting rate" value={`${dashboard.meeting_rate.toFixed(1)}%`} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="size-4" />
            Funnel
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  type="category"
                  dataKey="stage"
                  width={110}
                  tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "13px",
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={28}>
                  {chartData.map((entry) => (
                    <Cell key={entry.stage} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
