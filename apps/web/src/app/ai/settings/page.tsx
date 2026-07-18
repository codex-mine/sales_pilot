"use client";

import { PermissionGuard } from "@/components/guards";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useAISettings } from "@/features/ai/hooks/use-ai-settings";
import { AIProviderSettingsCard } from "@/features/ai/components/ai-provider-settings-card";

function AISettingsContent(): React.ReactElement {
  const { settings, isLoading, isError, errorMessage } = useAISettings();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-48 w-full" />
        ))}
      </div>
    );
  }

  if (isError || !settings) {
    return <ErrorState description={errorMessage ?? "Failed to load AI settings."} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {settings.providers.map((status) => (
        <AIProviderSettingsCard key={status.provider} status={status} />
      ))}
    </div>
  );
}

export default function AISettingsPage(): React.ReactElement {
  return (
    <PermissionGuard permission="ai.manage" fallback={<ErrorState description="You don't have access to AI settings." />}>
      <AISettingsContent />
    </PermissionGuard>
  );
}
