"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, DollarSign, Zap } from "@/icons";
import type { AIUsageAnalyticsResponse } from "../types";

export interface AIActivityWidgetProps {
  usage: AIUsageAnalyticsResponse | undefined;
  isLoading: boolean;
}

export function AIActivityWidget({ usage, isLoading }: AIActivityWidgetProps): React.ReactElement {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="size-4" />
          AI Activity & Cost
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading ? (
          <>
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-40 w-full" />
          </>
        ) : !usage || usage.total_job_count === 0 ? (
          <p className="py-8 text-center text-body-sm text-muted-foreground">No AI activity yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                <span className="flex items-center gap-1 text-caption text-muted-foreground">
                  <DollarSign className="size-3.5" />
                  Cost (24h)
                </span>
                <span className="text-heading-6 font-semibold text-foreground">${usage.total_cost_usd.toFixed(2)}</span>
              </div>
              <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                <span className="flex items-center gap-1 text-caption text-muted-foreground">
                  <Zap className="size-3.5" />
                  Jobs (24h)
                </span>
                <span className="text-heading-6 font-semibold text-foreground">{usage.total_job_count}</span>
              </div>
              <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                <span className="text-caption text-muted-foreground">Tokens (24h)</span>
                <span className="text-heading-6 font-semibold text-foreground">{usage.total_tokens.toLocaleString()}</span>
              </div>
            </div>

            {usage.by_job_type.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {usage.by_job_type.map((item) => (
                  <Badge key={item.job_type} variant="outline">
                    {item.job_type}: ${item.cost_usd.toFixed(2)}
                  </Badge>
                ))}
              </div>
            )}

            {usage.daily_cost_trend.length > 1 && (
              <div className="h-32 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={usage.daily_cost_trend} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={{ stroke: "hsl(var(--border))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={40} tickFormatter={(v: number) => `$${v}`} />
                    <Tooltip
                      formatter={(value: number) => `$${value.toFixed(2)}`}
                      contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "13px" }}
                    />
                    <Line type="monotone" dataKey="cost_usd" name="Cost" stroke="hsl(var(--info))" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
