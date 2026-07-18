"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AreaChart } from "@/components/charts/area-chart";
import type { ChartConfig } from "@/components/charts/chart-container";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import { TrendingUp } from "@/icons";
import { useAIUsage } from "../hooks/use-ai-usage";
import { AI_AGENT_TYPE_LABELS, type AIAgentType } from "../types";

const chartConfig: ChartConfig = {
  cost_usd: { label: "Spend", color: "hsl(var(--chart-1))" },
};

/** Total spend, trend, and per-job-type breakdown — reads AIJobService.usage() via GET /ai/usage. */
export function AICostWidget(): React.ReactElement {
  const { usage, isLoading } = useAIUsage(30);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI spend</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!usage || usage.total_jobs === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI spend</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={TrendingUp}
            title="No AI activity yet"
            description="Spend and usage will appear here once agents start running."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row items-baseline justify-between space-y-0">
        <CardTitle>AI spend (last 30 days)</CardTitle>
        <div className="flex items-baseline gap-1">
          <span className="text-heading-3 font-semibold text-foreground">
            {formatCurrency(usage.total_cost_usd)}
          </span>
          <span className="text-body-sm text-muted-foreground">
            · {formatCurrency(usage.all_time_cost_usd)} all-time
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {usage.daily_costs.length > 1 ? (
          <AreaChart
            data={usage.daily_costs as unknown as Record<string, unknown>[]}
            config={chartConfig}
            xKey="date"
            height={200}
            showLegend={false}
          />
        ) : (
          <p className="text-body-sm text-muted-foreground">Not enough daily data yet for a trend.</p>
        )}

        <div className="flex flex-col gap-2">
          <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">By job type</p>
          {usage.by_job_type.map((row) => (
            <div key={row.job_type} className="flex items-center justify-between text-body-sm">
              <span className="text-foreground">
                {AI_AGENT_TYPE_LABELS[row.job_type as AIAgentType] ?? row.job_type}
              </span>
              <span className="text-muted-foreground">
                {row.job_count} jobs · {formatCurrency(row.cost_usd)}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
