"use client";

import {
  CartesianGrid,
  Line,
  LineChart as RechartsLineChart,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart-container";

export interface LineChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  /** Data key used for the X axis categories (e.g. "date"). */
  xKey: string;
  /** Data keys rendered as lines — defaults to every key in `config`. */
  series?: string[];
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  className?: string;
}

/** A multi-series line chart — trends over time (pipeline value, email opens, AI job volume). */
export function LineChart({
  data,
  config,
  xKey,
  series,
  height = 320,
  showLegend = true,
  showGrid = true,
  className,
}: LineChartProps): React.ReactElement {
  const keys = series ?? Object.keys(config);

  return (
    <ChartContainer config={config} className={className} style={{ height }}>
      <RechartsLineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 0 }}>
        {showGrid && <CartesianGrid vertical={false} strokeDasharray="3 3" />}
        <XAxis
          dataKey={xKey}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          fontSize={12}
        />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} fontSize={12} width={32} />
        <ChartTooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltipContent config={config} />} />
        {showLegend && <ChartLegend content={<ChartLegendContent config={config} />} />}
        {keys.map((key) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={`var(--color-${key})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </RechartsLineChart>
    </ChartContainer>
  );
}
