"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Plus } from "@/icons";
import { usePromptTemplates } from "../hooks/use-prompt-templates";
import { usePromptVersions } from "../hooks/use-prompt-versions";
import { PromptVersionFormDialog } from "./prompt-version-form-dialog";
import { PromptVersionHistory } from "./prompt-version-history";
import { AI_AGENT_TYPE_LABELS, type AIAgentType } from "../types";

/** Prompt Template manager: list templates, browse version history, create + activate new versions. */
export function PromptTemplateManager(): React.ReactElement {
  const { templates, isLoading } = usePromptTemplates();
  const [activeTemplateId, setActiveTemplateId] = useState<string | undefined>(undefined);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);

  const selectedTemplateId = activeTemplateId ?? templates[0]?.id;
  const { versions } = usePromptVersions(selectedTemplateId);
  const activeVersion = versions.find((v) => v.is_active);

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }

  if (templates.length === 0) {
    return <EmptyState icon={FileText} title="No prompt templates yet" description="System templates are seeded automatically for every organization." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <Tabs value={selectedTemplateId} onValueChange={setActiveTemplateId}>
        <TabsList className="flex-wrap">
          {templates.map((template) => (
            <TabsTrigger key={template.id} value={template.id}>
              {template.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {templates.map((template) => (
          <TabsContent key={template.id} value={template.id} className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {template.is_system && (
                  <Badge variant="soft" size="sm">
                    System
                  </Badge>
                )}
                {template.agent_type && (
                  <Badge variant="outline" size="sm">
                    {AI_AGENT_TYPE_LABELS[template.agent_type as AIAgentType] ?? template.agent_type}
                  </Badge>
                )}
                <span className="text-body-sm text-muted-foreground">{template.description}</span>
              </div>
              <Button size="sm" onClick={() => setVersionDialogOpen(true)}>
                <Plus className="size-4" />
                New version
              </Button>
            </div>

            <PromptVersionHistory templateId={template.id} />
          </TabsContent>
        ))}
      </Tabs>

      {selectedTemplateId && (
        <PromptVersionFormDialog
          open={versionDialogOpen}
          onOpenChange={setVersionDialogOpen}
          templateId={selectedTemplateId}
          baseVersion={activeVersion}
        />
      )}
    </div>
  );
}
