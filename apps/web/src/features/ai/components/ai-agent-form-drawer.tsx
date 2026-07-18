"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreateAIAgent, useUpdateAIAgent } from "../hooks/use-ai-agent-mutations";
import { aiAgentFormSchema, type AIAgentFormValues } from "../schemas";
import {
  AI_AGENT_TYPE_CHOICES,
  AI_AGENT_TYPE_LABELS,
  LLM_PROVIDER_CHOICES,
  LLM_PROVIDER_LABELS,
  type AIAgentResponse,
} from "../types";

export interface AIAgentFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  agent?: AIAgentResponse;
  /** Pre-select an agent type when creating from an "add agent for this type" action. */
  defaultAgentType?: AIAgentFormValues["agent_type"];
}

function toFormValues(agent?: AIAgentResponse, defaultAgentType?: AIAgentFormValues["agent_type"]): AIAgentFormValues {
  return {
    name: agent?.name ?? "",
    agent_type: (agent?.agent_type as AIAgentFormValues["agent_type"]) ?? defaultAgentType ?? "research",
    description: agent?.description ?? "",
    provider: (agent?.provider as AIAgentFormValues["provider"]) ?? "anthropic",
    model_name: agent?.model_name ?? "",
    temperature: agent?.temperature ?? 0.7,
    max_tokens: agent?.max_tokens ?? 2048,
    is_active: agent?.is_active ?? true,
  };
}

/** Shared create/edit form for an AI Agent (provider/model/temperature config per agent type). */
export function AIAgentFormDrawer({ open, onOpenChange, agent, defaultAgentType }: AIAgentFormDrawerProps): React.ReactElement {
  const isEditing = Boolean(agent);
  const { createAgent, isCreating } = useCreateAIAgent();
  const { updateAgent, isUpdating } = useUpdateAIAgent();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<AIAgentFormValues>({
    resolver: zodResolver(aiAgentFormSchema),
    defaultValues: toFormValues(agent, defaultAgentType),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(agent, defaultAgentType));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, agent, defaultAgentType]);

  async function onSubmit(values: AIAgentFormValues): Promise<void> {
    const payload = {
      name: values.name,
      description: values.description || undefined,
      provider: values.provider,
      model_name: values.model_name,
      temperature: values.temperature,
      max_tokens: values.max_tokens,
      is_active: values.is_active,
    };
    try {
      if (isEditing && agent) {
        await updateAgent({ agentId: agent.id, payload });
      } else {
        await createAgent({ ...payload, agent_type: values.agent_type });
      }
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-w-lg">
        <DrawerHeader>
          <DrawerTitle>{isEditing ? "Edit AI agent" : "Configure AI agent"}</DrawerTitle>
          <DrawerDescription>
            {isEditing
              ? "Update this agent's provider, model, and behavior."
              : "One agent per capability — choose the provider and model it should use."}
          </DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form
            id="ai-agent-form"
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-1 flex-col gap-4 overflow-y-auto"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Research agent" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="agent_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Capability</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange} disabled={isEditing}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {AI_AGENT_TYPE_CHOICES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {AI_AGENT_TYPE_LABELS[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="provider"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Provider</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {LLM_PROVIDER_CHOICES.map((provider) => (
                          <SelectItem key={provider} value={provider}>
                            {LLM_PROVIDER_LABELS[provider]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="model_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Model</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. claude-sonnet-5" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="temperature"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Temperature (0–2)</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} max={2} step={0.1} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="max_tokens"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Max tokens</FormLabel>
                    <FormControl>
                      <Input type="number" min={1} max={200000} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea rows={2} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border border-border p-3">
                  <div>
                    <FormLabel>Active</FormLabel>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DrawerFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="ai-agent-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Create agent"}
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
