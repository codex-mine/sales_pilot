"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart as RechartsRadarChart,
} from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart-container";

export interface RadarChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  /** Data key used for the polar categories (e.g. "skill"). */
  angleKey: string;
  series?: string[];
  height?: number;
  showLegend?: boolean;
  className?: string;
}

/** A radar/spider chart — multi-dimensional comparisons (rep scorecards, ICP fit criteria). */
export function RadarChart({
  data,
  config,
  angleKey,
  series,
  height = 320,
  showLegend = true,
  className,
}: RadarChartProps): React.ReactElement {
  const keys = series ?? Object.keys(config);

  return (
    <ChartContainer config={config} className={className} style={{ height }}>
      <RechartsRadarChart data={data}>
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis dataKey={angleKey} fontSize={12} tick={{ fill: "hsl(var(--muted-foreground))" }} />
        <ChartTooltip content={<ChartTooltipContent config={config} />} />
        {showLegend && <ChartLegend content={<ChartLegendContent config={config} />} />}
        {keys.map((key) => (
          <Radar
            key={key}
            dataKey={key}
            stroke={`var(--color-${key})`}
            fill={`var(--color-${key})`}
            fillOpacity={0.2}
            strokeWidth={2}
          />
        ))}
      </RechartsRadarChart>
    </ChartContainer>
  );
}
