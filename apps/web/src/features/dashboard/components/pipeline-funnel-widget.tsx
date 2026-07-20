"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { GitBranch } from "@/icons";
import { LEAD_STATUS_LABELS, type LeadStatus } from "@/features/leads/types";
import type { PipelineFunnelResponse } from "../types";

// The named funnel stages a sales leader scans first, in pipeline order —
// a deliberate subset of the full LeadStatusEnum (see PipelineFunnelResponse,
// which carries every status) so the chart stays a readable funnel shape.
const FUNNEL_STAGES: LeadStatus[] = [
  "new", "researching", "contacted", "opened", "replied", "interested", "demo_scheduled", "won",
];

export interface PipelineFunnelWidgetProps {
  funnel: PipelineFunnelResponse | undefined;
  isLoading: boolean;
}

export function PipelineFunnelWidget({ funnel, isLoading }: PipelineFunnelWidgetProps): React.ReactElement {
  const chartData = FUNNEL_STAGES.map((status) => ({
    stage: LEAD_STATUS_LABELS[status],
    count: funnel?.counts[status] ?? 0,
  }));
  const hasData = chartData.some((row) => row.count > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitBranch className="size-4" />
          Pipeline Funnel
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : !hasData ? (
          <p className="py-8 text-center text-body-sm text-muted-foreground">No leads in the pipeline yet.</p>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis
                  type="number" allowDecimals={false}
                  tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false} axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  type="category" dataKey="stage" width={100}
                  tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))",
                    borderRadius: "8px", fontSize: "13px",
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={24}>
                  {chartData.map((entry) => (
                    <Cell key={entry.stage} fill="hsl(var(--primary))" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
