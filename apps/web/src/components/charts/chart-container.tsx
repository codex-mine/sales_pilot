"use client";

import { useId, type ComponentProps, type ReactNode } from "react";
import * as RechartsPrimitive from "recharts";
import { cn } from "@/lib/utils";

/**
 * Chart color configuration. Each series maps to a `--chart-N` token (see
 * globals.css) so every chart in the app draws from the same 5-color
 * sequence — no chart ever picks its own ad-hoc hex value.
 */
export interface ChartSeriesConfig {
  label: ReactNode;
  color?: string;
  icon?: React.ComponentType;
}
export type ChartConfig = Record<string, ChartSeriesConfig>;

const THEME_COLOR_VARS = ["chart-1", "chart-2", "chart-3", "chart-4", "chart-5"] as const;

/** Assigns `--chart-1 … --chart-5` to config entries in declaration order when no explicit `color` is given. */
function resolveChartStyle(config: ChartConfig): string {
  return Object.entries(config)
    .map(([key, value], index) => {
      const color = value.color ?? `hsl(var(--${THEME_COLOR_VARS[index % THEME_COLOR_VARS.length]}))`;
      return `--color-${key}: ${color};`;
    })
    .join(" ");
}

export interface ChartContainerProps extends ComponentProps<"div"> {
  config: ChartConfig;
  children: ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
}

/** Wraps any Recharts chart in a themed, responsive container. Always the outermost element for a chart. */
export function ChartContainer({ config, className, children, ...props }: ChartContainerProps): React.ReactElement {
  const uid = useId();

  return (
    <div
      data-chart={uid}
      className={cn(
        "aspect-video w-full text-caption",
        "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground",
        "[&_.recharts-cartesian-grid_line]:stroke-border",
        "[&_.recharts-reference-line_line]:stroke-border",
        "[&_.recharts-dot]:stroke-transparent",
        "[&_.recharts-layer]:outline-none",
        "[&_.recharts-sector]:outline-none",
        "[&_.recharts-surface]:outline-none",
        className,
      )}
      style={{ ["--chart-style" as string]: resolveChartStyle(config) }}
      {...props}
    >
      <style>{`[data-chart="${uid}"] { ${resolveChartStyle(config)} }`}</style>
      <RechartsPrimitive.ResponsiveContainer width="100%" height="100%">
        {children}
      </RechartsPrimitive.ResponsiveContainer>
    </div>
  );
}

export const ChartTooltip = RechartsPrimitive.Tooltip;

export interface ChartTooltipContentProps extends ComponentProps<typeof RechartsPrimitive.Tooltip> {
  config: ChartConfig;
  labelFormatter?: (label: string) => ReactNode;
  valueFormatter?: (value: number | string) => ReactNode;
}

/** Token-styled tooltip content — pass as `<ChartTooltip content={<ChartTooltipContent config={config} />} />`. */
export function ChartTooltipContent({
  active,
  payload,
  label,
  config,
  labelFormatter,
  valueFormatter,
}: ChartTooltipContentProps & Record<string, unknown>): React.ReactElement | null {
  if (!active || !payload?.length) return null;

  return (
    <div className="min-w-32 rounded-md border border-border bg-popover p-2.5 text-popover-foreground shadow-popover">
      {label !== undefined && (
        <p className="mb-1.5 text-caption font-medium text-muted-foreground">
          {labelFormatter ? labelFormatter(String(label)) : label}
        </p>
      )}
      <div className="flex flex-col gap-1">
        {payload.map((entry, index) => {
          const key = String(entry.dataKey ?? entry.name ?? index);
          const seriesConfig = config[key];
          return (
            <div key={key} className="flex items-center justify-between gap-4 text-body-sm">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: entry.color }}
                  aria-hidden="true"
                />
                {seriesConfig?.label ?? key}
              </span>
              <span className="font-medium tabular-nums text-foreground">
                {valueFormatter ? valueFormatter(entry.value as number) : entry.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const ChartLegend = RechartsPrimitive.Legend;

export function ChartLegendContent({ config }: { config: ChartConfig }): React.ReactElement {
  return (
    <div className="flex flex-wrap items-center justify-center gap-4 pt-3">
      {Object.entries(config).map(([key, value]) => (
        <span key={key} className="flex items-center gap-1.5 text-caption text-muted-foreground">
          <span
            className="size-2 shrink-0 rounded-full"
            style={{ backgroundColor: `var(--color-${key})` }}
            aria-hidden="true"
          />
          {value.label}
        </span>
      ))}
    </div>
  );
}
