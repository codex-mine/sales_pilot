"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, Mail, MousePointerClick, XCircle } from "@/icons";
import { useEmailPerformanceAnalytics } from "../hooks/use-email-performance-analytics";

const WINDOW_OPTIONS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
];

function StatTile({
  icon: Icon, label, value, tone,
}: {
  icon: typeof Mail;
  label: string;
  value: string;
  tone: "success" | "info" | "danger";
}): React.ReactElement {
  const toneClass = { success: "text-success", info: "text-info", danger: "text-danger" }[tone];
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border p-4">
      <div className={`flex items-center gap-1.5 text-caption ${toneClass}`}>
        <Icon className="size-3.5" />
        {label}
      </div>
      <span className="text-heading-4 font-semibold text-foreground">{value}</span>
    </div>
  );
}

/** Open rate / click rate / bounce rate over time — the underlying chart
 * for the org-wide Email Performance dashboard (module 12 embeds this
 * widget; this module owns the data it reads). */
export function EmailPerformanceWidget(): React.ReactElement {
  const [days, setDays] = useState(30);
  const { analytics, isLoading, isError, errorMessage, refetch } = useEmailPerformanceAnalytics({ days });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="size-4" />
          Email Performance
        </CardTitle>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {WINDOW_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {isLoading ? (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-3 gap-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
            <Skeleton className="h-64 w-full" />
          </div>
        ) : isError ? (
          <ErrorState title="Couldn't load analytics" description={errorMessage ?? undefined} onRetry={refetch} />
        ) : !analytics || analytics.total_sent === 0 ? (
          <EmptyState
            icon={Mail}
            title="No emails sent yet"
            description="Once you start sending, open/click/bounce rates will show up here."
          />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <StatTile
                icon={Mail} label="Open rate" tone="success"
                value={`${(analytics.open_rate * 100).toFixed(1)}%`}
              />
              <StatTile
                icon={MousePointerClick} label="Click rate" tone="info"
                value={`${(analytics.click_rate * 100).toFixed(1)}%`}
              />
              <StatTile
                icon={XCircle} label="Bounce rate" tone="danger"
                value={`${(analytics.bounce_rate * 100).toFixed(1)}%`}
              />
            </div>

            {analytics.daily.length > 0 && (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics.daily} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={{ stroke: "hsl(var(--border))" }}
                    />
                    <YAxis
                      tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      width={40}
                    />
                    <Tooltip
                      formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "13px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "13px" }} />
                    <Line
                      type="monotone" dataKey="open_rate" name="Open rate"
                      stroke="hsl(var(--success))" strokeWidth={2} dot={false}
                    />
                    <Line
                      type="monotone" dataKey="click_rate" name="Click rate"
                      stroke="hsl(var(--info))" strokeWidth={2} dot={false}
                    />
                    <Line
                      type="monotone" dataKey="bounce_rate" name="Bounce rate"
                      stroke="hsl(var(--danger))" strokeWidth={2} dot={false}
                    />
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
