"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usePromptVersions } from "../hooks/use-prompt-versions";
import { useActivatePromptVersion } from "../hooks/use-prompt-mutations";
import type { PromptVersionResponse } from "../types";

export interface PromptVersionHistoryProps {
  templateId: string;
}

/** Git-log-style version list for one prompt template — select two versions to diff, activate any past version. */
export function PromptVersionHistory({ templateId }: PromptVersionHistoryProps): React.ReactElement {
  const { versions, isLoading } = usePromptVersions(templateId);
  const { activateVersion, isActivating } = useActivatePromptVersion();
  const [selected, setSelected] = useState<[PromptVersionResponse | null, PromptVersionResponse | null]>([
    null,
    null,
  ]);
  const [activatingVersion, setActivatingVersion] = useState<PromptVersionResponse | undefined>(undefined);

  function toggleSelect(version: PromptVersionResponse): void {
    setSelected(([a, b]) => {
      if (a?.id === version.id) return [b, null];
      if (b?.id === version.id) return [a, null];
      if (!a) return [version, b];
      if (!b) return [a, version];
      return [b, version];
    });
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  const [left, right] = selected;

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-2">
        {versions.map((version) => (
          <li
            key={version.id}
            className={cn(
              "flex items-center justify-between gap-3 rounded-lg border border-border p-3 text-body-sm",
              (left?.id === version.id || right?.id === version.id) && "border-primary bg-accent/40",
            )}
          >
            <button
              type="button"
              onClick={() => toggleSelect(version)}
              className="flex flex-1 items-center gap-3 text-left"
            >
              <span className="font-mono font-medium text-foreground">v{version.version_number}</span>
              {version.is_active && <Badge variant="success" size="sm">Active</Badge>}
              <span className="truncate text-muted-foreground">{version.change_notes || "No notes"}</span>
            </button>
            <div className="flex shrink-0 items-center gap-3">
              <span className="text-caption text-muted-foreground">
                {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
              </span>
              {!version.is_active && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setActivatingVersion(version)}
                >
                  Activate
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {left && right && (
        <div className="flex flex-col gap-2">
          <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
            Comparing v{Math.min(left.version_number, right.version_number)} → v{Math.max(left.version_number, right.version_number)}
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[left, right]
              .sort((a, b) => a.version_number - b.version_number)
              .map((version) => (
                <div key={version.id} className="flex flex-col gap-2 rounded-lg border border-border p-3">
                  <p className="text-caption font-medium text-foreground">v{version.version_number}</p>
                  <div>
                    <p className="text-caption text-muted-foreground">System prompt</p>
                    <pre className="whitespace-pre-wrap text-caption text-foreground">{version.system_prompt}</pre>
                  </div>
                  <div>
                    <p className="text-caption text-muted-foreground">User prompt template</p>
                    <pre className="whitespace-pre-wrap text-caption text-foreground">
                      {version.user_prompt_template}
                    </pre>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(activatingVersion)}
        onOpenChange={(open) => !open && setActivatingVersion(undefined)}
        title={`Activate version ${activatingVersion?.version_number}?`}
        description="This changes live behavior — every new AI job for this template will use this version immediately."
        confirmLabel="Activate"
        confirmVariant="primary"
        isConfirming={isActivating}
        onConfirm={async () => {
          if (activatingVersion) {
            await activateVersion({ templateId, versionId: activatingVersion.id });
            setActivatingVersion(undefined);
          }
        }}
      />
    </div>
  );
}
