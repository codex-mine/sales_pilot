"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, Pencil, Plus, Trash2 } from "@/icons";
import { useAIAgents } from "../hooks/use-ai-agents";
import { useDeleteAIAgent } from "../hooks/use-ai-agent-mutations";
import { AIAgentFormDrawer } from "./ai-agent-form-drawer";
import { AI_AGENT_TYPE_LABELS, LLM_PROVIDER_LABELS, type AIAgentResponse, type AIAgentType, type LLMProvider } from "../types";

/** Lists every configured AI Agent (one per capability) with edit/delete, plus an "add" action for unconfigured capabilities. */
export function AIAgentsList(): React.ReactElement {
  const { agents, isLoading } = useAIAgents();
  const { deleteAgent, isDeleting } = useDeleteAIAgent();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AIAgentResponse | undefined>(undefined);
  const [deletingAgent, setDeletingAgent] = useState<AIAgentResponse | undefined>(undefined);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-40 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">
        <Button
          size="sm"
          onClick={() => {
            setEditingAgent(undefined);
            setDrawerOpen(true);
          }}
        >
          <Plus className="size-4" />
          Configure agent
        </Button>
      </div>

      {agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No agents configured yet"
          description="Every AI capability falls back to the platform default until you configure one here."
          action={
            <Button size="sm" onClick={() => setDrawerOpen(true)}>
              <Plus className="size-4" />
              Configure agent
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id}>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div className="flex flex-col gap-1">
                  <CardTitle className="text-heading-6">{agent.name}</CardTitle>
                  <Badge variant="soft" size="sm">
                    {AI_AGENT_TYPE_LABELS[agent.agent_type as AIAgentType] ?? agent.agent_type}
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                  <IconButton
                    icon={Pencil}
                    aria-label="Edit agent"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditingAgent(agent);
                      setDrawerOpen(true);
                    }}
                  />
                  <IconButton
                    icon={Trash2}
                    aria-label="Delete agent"
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeletingAgent(agent)}
                  />
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 text-body-sm text-muted-foreground">
                <p>
                  {LLM_PROVIDER_LABELS[agent.provider as LLMProvider] ?? agent.provider} · {agent.model_name}
                </p>
                <p>
                  Temperature {agent.temperature.toFixed(1)} · {agent.max_tokens.toLocaleString()} max tokens
                </p>
                {!agent.is_active && (
                  <Badge variant="outline" size="sm" className="mt-1 w-fit">
                    Disabled
                  </Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AIAgentFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} agent={editingAgent} />

      <ConfirmDialog
        open={Boolean(deletingAgent)}
        onOpenChange={(open) => !open && setDeletingAgent(undefined)}
        title="Delete this agent?"
        description={`"${deletingAgent?.name}" will stop being used — its capability falls back to the platform default.`}
        confirmLabel="Delete"
        isConfirming={isDeleting}
        onConfirm={async () => {
          if (deletingAgent) {
            await deleteAgent(deletingAgent.id);
            setDeletingAgent(undefined);
          }
        }}
      />
    </div>
  );
}
