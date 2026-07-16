"use client";

import { Bar, CartesianGrid, BarChart as RechartsBarChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart-container";

export interface BarChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  xKey: string;
  series?: string[];
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  /** Stacks all series in a single bar per category instead of grouping them side by side. */
  stacked?: boolean;
  className?: string;
}

/** A grouped or stacked bar chart — comparisons across categories (leads by source, revenue by rep). */
export function BarChart({
  data,
  config,
  xKey,
  series,
  height = 320,
  showLegend = true,
  showGrid = true,
  stacked = false,
  className,
}: BarChartProps): React.ReactElement {
  const keys = series ?? Object.keys(config);

  return (
    <ChartContainer config={config} className={className} style={{ height }}>
      <RechartsBarChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 0 }}>
        {showGrid && <CartesianGrid vertical={false} strokeDasharray="3 3" />}
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} tickMargin={8} fontSize={12} />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} fontSize={12} width={32} />
        <ChartTooltip cursor={{ fill: "hsl(var(--muted))" }} content={<ChartTooltipContent config={config} />} />
        {showLegend && <ChartLegend content={<ChartLegendContent config={config} />} />}
        {keys.map((key) => (
          <Bar
            key={key}
            dataKey={key}
            fill={`var(--color-${key})`}
            radius={stacked ? 0 : [4, 4, 0, 0]}
            stackId={stacked ? "stack" : undefined}
            maxBarSize={40}
          />
        ))}
      </RechartsBarChart>
    </ChartContainer>
  );
}
