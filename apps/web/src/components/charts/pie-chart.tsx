"use client";

import { Cell, Pie, PieChart as RechartsPieChart } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart-container";

export interface PieChartDatum {
  name: string;
  value: number;
}

export interface PieChartProps {
  data: PieChartDatum[];
  config: ChartConfig;
  height?: number;
  showLegend?: boolean;
  /** 0 renders a full pie; > 0 renders a donut. `DonutChart` below just presets this to 60. */
  innerRadius?: number;
  className?: string;
}

/** A pie (or donut, via `innerRadius`) chart for part-to-whole breakdowns — leads by status, revenue by plan. */
export function PieChart({
  data,
  config,
  height = 320,
  showLegend = true,
  innerRadius = 0,
  className,
}: PieChartProps): React.ReactElement {
  return (
    <ChartContainer config={config} className={className} style={{ height }}>
      <RechartsPieChart>
        <ChartTooltip content={<ChartTooltipContent config={config} />} />
        {showLegend && <ChartLegend content={<ChartLegendContent config={config} />} />}
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={innerRadius}
          outerRadius="80%"
          paddingAngle={2}
          strokeWidth={2}
        >
          {data.map((entry) => (
            <Cell key={entry.name} fill={`var(--color-${entry.name})`} stroke="hsl(var(--card))" />
          ))}
        </Pie>
      </RechartsPieChart>
    </ChartContainer>
  );
}

/** A PieChart preset with a hollow center — same data/config shape as PieChart. */
export function DonutChart(props: Omit<PieChartProps, "innerRadius">): React.ReactElement {
  return <PieChart {...props} innerRadius={64} />;
}
