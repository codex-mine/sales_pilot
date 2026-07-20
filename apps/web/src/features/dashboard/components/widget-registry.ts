import type { IconComponent } from "@/icons";
import { Bot, CalendarDays, GitBranch, History, Mail, Rocket } from "@/icons";

export interface WidgetDefinition {
  widgetType: string;
  title: string;
  icon: IconComponent;
  description: string;
}

// The fixed set of widget types this dashboard knows how to render — content
// per widget is hardcoded (not arbitrary/user-defined), so "customization"
// means picking which of these to show, not building new ones.
export const WIDGET_DEFINITIONS: WidgetDefinition[] = [
  { widgetType: "pipeline_funnel", title: "Pipeline Funnel", icon: GitBranch, description: "Leads by pipeline stage" },
  { widgetType: "ai_usage", title: "AI Activity & Cost", icon: Bot, description: "AI job spend and volume" },
  { widgetType: "email_performance", title: "Email Performance", icon: Mail, description: "Open, click, and bounce rates" },
  { widgetType: "campaign_performance", title: "Campaign Performance", icon: Rocket, description: "Top campaigns by reply rate" },
  { widgetType: "meetings", title: "Meetings", icon: CalendarDays, description: "Upcoming meetings and this month's bookings" },
  { widgetType: "recent_activity", title: "Recent Activity", icon: History, description: "Org-wide activity feed" },
];

export const DEFAULT_WIDGET_TYPES = WIDGET_DEFINITIONS.map((w) => w.widgetType);
