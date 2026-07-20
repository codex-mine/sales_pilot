"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ResponsiveGrid } from "@/components/layout/responsive-grid";
import { LayoutDashboard, Plus, Rocket, Users } from "@/icons";
import { EmailPerformanceWidget } from "@/features/analytics/components/email-performance-widget";
import { useAddDashboardWidget, useRemoveDashboardWidget } from "../hooks/use-dashboard-widget-mutations";
import { useDashboardSummary } from "../hooks/use-dashboard-summary";
import { useDashboardWidgets } from "../hooks/use-dashboard-widgets";
import { AddWidgetDialog } from "./add-widget-dialog";
import { AIActivityWidget } from "./ai-activity-widget";
import { CampaignPerformanceWidget } from "./campaign-performance-widget";
import { DashboardWidgetFrame } from "./dashboard-widget-frame";
import { MeetingsWidget } from "./meetings-widget";
import { PipelineFunnelWidget } from "./pipeline-funnel-widget";
import { RecentActivityWidget } from "./recent-activity-widget";
import { DEFAULT_WIDGET_TYPES, WIDGET_DEFINITIONS } from "./widget-registry";

export function DashboardContent(): React.ReactElement {
  const { summary, isLoading, isError, errorMessage, refetch } = useDashboardSummary();
  const { widgets, isLoading: widgetsLoading } = useDashboardWidgets();
  const { addWidget, isAdding } = useAddDashboardWidget();
  const { removeWidget } = useRemoveDashboardWidget();
  const [addOpen, setAddOpen] = useState(false);
  const hasSeeded = useRef(false);

  // First-ever visit: seed the user's default widget set once so add/remove
  // always has real DashboardWidget rows to work against — see
  // widget-registry.ts's DEFAULT_WIDGET_TYPES.
  useEffect(() => {
    if (widgetsLoading || hasSeeded.current || widgets.length > 0) return;
    hasSeeded.current = true;
    DEFAULT_WIDGET_TYPES.forEach((widgetType, index) => {
      const definition = WIDGET_DEFINITIONS.find((w) => w.widgetType === widgetType);
      if (!definition) return;
      void addWidget({ widget_type: widgetType, title: definition.title, position_y: index });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once, guarded by hasSeeded
  }, [widgetsLoading, widgets.length]);

  if (isError) {
    return <ErrorState title="Couldn't load dashboard" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  const visibleTypes = widgets.length > 0 ? widgets.map((w) => w.widget_type) : DEFAULT_WIDGET_TYPES;
  const isNewOrganization =
    !isLoading &&
    summary !== undefined &&
    Object.values(summary.pipeline_funnel.counts).every((count) => count === 0) &&
    summary.campaign_performance.campaigns.length === 0 &&
    summary.ai_usage.total_job_count === 0 &&
    summary.meetings.upcoming.length === 0;

  function widgetIdFor(widgetType: string): string | undefined {
    return widgets.find((w) => w.widget_type === widgetType)?.id;
  }

  function renderWidget(widgetType: string): React.ReactNode {
    switch (widgetType) {
      case "pipeline_funnel":
        return <PipelineFunnelWidget funnel={summary?.pipeline_funnel} isLoading={isLoading} />;
      case "ai_usage":
        return <AIActivityWidget usage={summary?.ai_usage} isLoading={isLoading} />;
      case "email_performance":
        return <EmailPerformanceWidget />;
      case "campaign_performance":
        return <CampaignPerformanceWidget performance={summary?.campaign_performance} isLoading={isLoading} />;
      case "meetings":
        return <MeetingsWidget meetings={summary?.meetings} isLoading={isLoading} />;
      case "recent_activity":
        return <RecentActivityWidget activity={summary?.recent_activity} isLoading={isLoading} />;
      default:
        return null;
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {isNewOrganization && (
        <EmptyState
          icon={LayoutDashboard}
          title="Welcome to SalesPilot"
          description="Your dashboard fills in as you add leads and launch campaigns. Start by adding your first lead or setting up a campaign."
          action={
            <div className="flex gap-2">
              <Button size="sm" asChild>
                <Link href="/leads">
                  <Users className="size-4" />
                  Add a lead
                </Link>
              </Button>
              <Button size="sm" variant="outline" asChild>
                <Link href="/campaigns">
                  <Rocket className="size-4" />
                  Create a campaign
                </Link>
              </Button>
            </div>
          }
        />
      )}

      <div className="flex items-center justify-end">
        <Button size="sm" variant="outline" onClick={() => setAddOpen(true)}>
          <Plus className="size-4" />
          Add widget
        </Button>
      </div>

      <ResponsiveGrid cols={{ base: 1, lg: 2 }} gap="md">
        {visibleTypes.map((widgetType) => (
          <DashboardWidgetFrame
            key={widgetType}
            onRemove={
              widgetIdFor(widgetType) ? () => void removeWidget(widgetIdFor(widgetType) as string) : undefined
            }
          >
            {renderWidget(widgetType)}
          </DashboardWidgetFrame>
        ))}
      </ResponsiveGrid>

      <AddWidgetDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        visibleWidgetTypes={visibleTypes}
        isAdding={isAdding}
        onAdd={(widgetType) => {
          const definition = WIDGET_DEFINITIONS.find((w) => w.widgetType === widgetType);
          if (!definition) return;
          void addWidget({ widget_type: widgetType, title: definition.title, position_y: visibleTypes.length });
          setAddOpen(false);
        }}
      />
    </div>
  );
}
