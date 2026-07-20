"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Rocket } from "@/icons";
import type { CampaignPerformanceResponse } from "../types";

export interface CampaignPerformanceWidgetProps {
  performance: CampaignPerformanceResponse | undefined;
  isLoading: boolean;
}

export function CampaignPerformanceWidget({ performance, isLoading }: CampaignPerformanceWidgetProps): React.ReactElement {
  const campaigns = performance?.campaigns ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Rocket className="size-4" />
          Campaign Performance
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : campaigns.length === 0 ? (
          <p className="py-8 text-center text-body-sm text-muted-foreground">No active campaigns yet.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {campaigns.map((campaign) => (
              <Link
                key={campaign.campaign_id}
                href={`/campaigns/${campaign.campaign_id}`}
                className="flex items-center justify-between gap-3 rounded-md px-2 py-2 hover:bg-muted/60"
              >
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-body-sm font-medium text-foreground">{campaign.campaign_name}</span>
                  <span className="text-caption text-muted-foreground">{campaign.enrolled_count} enrolled</span>
                </div>
                <span className="shrink-0 text-body-sm font-semibold text-success">{campaign.reply_rate}%</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
