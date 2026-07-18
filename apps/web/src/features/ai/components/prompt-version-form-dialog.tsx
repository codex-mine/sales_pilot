"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreatePromptVersion } from "../hooks/use-prompt-mutations";
import { promptVersionFormSchema, type PromptVersionFormValues } from "../schemas";
import type { PromptVersionResponse } from "../types";

export interface PromptVersionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templateId: string;
  /** Pre-filled from the current active version — editing always creates version N+1, never mutates it. */
  baseVersion?: PromptVersionResponse;
}

export function PromptVersionFormDialog({
  open,
  onOpenChange,
  templateId,
  baseVersion,
}: PromptVersionFormDialogProps): React.ReactElement {
  const { createVersion, isCreating } = useCreatePromptVersion();

  const form = useForm<PromptVersionFormValues>({
    resolver: zodResolver(promptVersionFormSchema),
    defaultValues: {
      system_prompt: baseVersion?.system_prompt ?? "",
      user_prompt_template: baseVersion?.user_prompt_template ?? "",
      variables: baseVersion?.variables.join(", ") ?? "",
      change_notes: "",
      activate: false,
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        system_prompt: baseVersion?.system_prompt ?? "",
        user_prompt_template: baseVersion?.user_prompt_template ?? "",
        variables: baseVersion?.variables.join(", ") ?? "",
        change_notes: "",
        activate: false,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the dialog opens or the base version changes
  }, [open, baseVersion]);

  async function onSubmit(values: PromptVersionFormValues): Promise<void> {
    try {
      await createVersion({
        templateId,
        payload: {
          system_prompt: values.system_prompt,
          user_prompt_template: values.user_prompt_template,
          variables: values.variables
            ? values.variables.split(",").map((v) => v.trim()).filter(Boolean)
            : [],
          change_notes: values.change_notes || undefined,
          activate: values.activate,
        },
      });
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create new prompt version</DialogTitle>
          <DialogDescription>
            Versions are immutable — this creates a new version rather than editing the current one.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form id="prompt-version-form" onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="system_prompt"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>System prompt</FormLabel>
                  <FormControl>
                    <Textarea rows={4} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="user_prompt_template"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>User prompt template</FormLabel>
                  <FormControl>
                    <Textarea rows={4} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="variables"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Variables (comma-separated)</FormLabel>
                  <FormControl>
                    <Textarea rows={1} placeholder="company_name, context" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="change_notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Change notes</FormLabel>
                  <FormControl>
                    <Textarea rows={2} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="activate"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border border-border p-3">
                  <div>
                    <FormLabel>Activate immediately</FormLabel>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="prompt-version-form" isLoading={isCreating}>
            Create version
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
