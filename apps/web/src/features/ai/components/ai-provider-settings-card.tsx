"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useUpdateAISettings } from "../hooks/use-ai-settings";
import { aiSettingsFormSchema, type AISettingsFormValues } from "../schemas";
import { LLM_PROVIDER_LABELS, type AIProviderStatusResponse, type LLMProvider } from "../types";

export interface AIProviderSettingsCardProps {
  status: AIProviderStatusResponse;
}

/** One connect/disconnect card per LLM provider — never renders a stored key back, only a "Connected" badge. */
export function AIProviderSettingsCard({ status }: AIProviderSettingsCardProps): React.ReactElement {
  const provider = status.provider as LLMProvider;
  const isOllama = provider === "local";
  const { updateSettings, isUpdating } = useUpdateAISettings();
  const [removeConfirmOpen, setRemoveConfirmOpen] = useState(false);

  const form = useForm<AISettingsFormValues>({
    resolver: zodResolver(aiSettingsFormSchema),
    defaultValues: { provider, api_key: "", base_url: "" },
  });

  async function onSubmit(values: AISettingsFormValues): Promise<void> {
    try {
      await updateSettings({
        provider,
        api_key: isOllama ? undefined : values.api_key || undefined,
        base_url: isOllama ? values.base_url || undefined : undefined,
      });
      form.reset({ provider, api_key: "", base_url: "" });
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  async function handleRemove(): Promise<void> {
    await updateSettings({ provider, remove: true });
    setRemoveConfirmOpen(false);
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-heading-6">{LLM_PROVIDER_LABELS[provider]}</CardTitle>
        {status.has_org_key ? (
          <Badge variant="success">Connected</Badge>
        ) : status.has_platform_fallback ? (
          <Badge variant="info">Platform default</Badge>
        ) : (
          <Badge variant="outline">Not connected</Badge>
        )}
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3">
            {isOllama ? (
              <FormField
                control={form.control}
                name="base_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base URL</FormLabel>
                    <FormControl>
                      <Input placeholder="http://localhost:11434" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API key</FormLabel>
                    <FormControl>
                      <PasswordInput placeholder={status.has_org_key ? "••••••••••••" : "sk-..."} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            <div className="flex items-center gap-2">
              <Button type="submit" size="sm" isLoading={isUpdating}>
                Save
              </Button>
              {status.has_org_key && (
                <Button type="button" variant="outline" size="sm" onClick={() => setRemoveConfirmOpen(true)}>
                  Disconnect
                </Button>
              )}
            </div>
          </form>
        </Form>
      </CardContent>

      <ConfirmDialog
        open={removeConfirmOpen}
        onOpenChange={setRemoveConfirmOpen}
        title={`Disconnect ${LLM_PROVIDER_LABELS[provider]}?`}
        description="This organization will fall back to the platform default key, if one is configured."
        confirmLabel="Disconnect"
        isConfirming={isUpdating}
        onConfirm={handleRemove}
      />
    </Card>
  );
}
