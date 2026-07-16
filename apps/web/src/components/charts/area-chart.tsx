"use client";

import { Area, CartesianGrid, AreaChart as RechartsAreaChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart-container";

export interface AreaChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  xKey: string;
  series?: string[];
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  stacked?: boolean;
  className?: string;
}

/** A (optionally stacked) area chart — cumulative trends, e.g. pipeline value by stage over time. */
export function AreaChart({
  data,
  config,
  xKey,
  series,
  height = 320,
  showLegend = true,
  showGrid = true,
  stacked = false,
  className,
}: AreaChartProps): React.ReactElement {
  const keys = series ?? Object.keys(config);

  return (
    <ChartContainer config={config} className={className} style={{ height }}>
      <RechartsAreaChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 0 }}>
        <defs>
          {keys.map((key) => (
            <linearGradient key={key} id={`area-fill-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={`var(--color-${key})`} stopOpacity={0.35} />
              <stop offset="95%" stopColor={`var(--color-${key})`} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        {showGrid && <CartesianGrid vertical={false} strokeDasharray="3 3" />}
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} tickMargin={8} fontSize={12} />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} fontSize={12} width={32} />
        <ChartTooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltipContent config={config} />} />
        {showLegend && <ChartLegend content={<ChartLegendContent config={config} />} />}
        {keys.map((key) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={`var(--color-${key})`}
            strokeWidth={2}
            fill={`url(#area-fill-${key})`}
            stackId={stacked ? "stack" : undefined}
          />
        ))}
      </RechartsAreaChart>
    </ChartContainer>
  );
}
