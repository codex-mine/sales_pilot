"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useEmailTemplates } from "@/features/email-templates/hooks/use-email-templates";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreateSequenceStep, useUpdateSequenceStep } from "../hooks/use-sequence-mutations";
import { sequenceStepFormSchema, type SequenceStepFormValues } from "../schemas";
import { STEP_TYPE_LABELS, SUPPORTED_STEP_TYPES, type SequenceStepResponse } from "../types";

export interface SequenceStepFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  campaignId: string;
  sequenceId: string;
  /** Present for edit, absent for create (appended to the end). */
  step?: SequenceStepResponse;
  /** Order to assign a newly created step — ignored when editing. */
  nextStepOrder: number;
}

function toFormValues(step?: SequenceStepResponse): SequenceStepFormValues {
  return {
    step_type: (step?.step_type as SequenceStepFormValues["step_type"]) ?? "email",
    delay_days: step?.delay_days ?? 0,
    delay_hours: step?.delay_hours ?? 0,
    content_source: (step?.content_source as SequenceStepFormValues["content_source"]) ?? "template",
    email_template_id: step?.email_template_id ?? "",
    subject_override: step?.subject_override ?? "",
    body_override: step?.body_override ?? "",
    skip_if: step?.condition?.skip_if ?? "",
  };
}

const SKIP_IF_OPTIONS = [
  { value: "", label: "No condition" },
  { value: "opened", label: "Skip if opened previous email" },
  { value: "clicked", label: "Skip if clicked previous email" },
  { value: "replied", label: "Skip if replied" },
];

export function SequenceStepFormDialog({
  open,
  onOpenChange,
  campaignId,
  sequenceId,
  step,
  nextStepOrder,
}: SequenceStepFormDialogProps): React.ReactElement {
  const isEditing = Boolean(step);
  const { createStep, isCreating } = useCreateSequenceStep();
  const { updateStep, isUpdating } = useUpdateSequenceStep();
  const { templates } = useEmailTemplates({ page_size: 200, is_active: true });
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<SequenceStepFormValues>({
    resolver: zodResolver(sequenceStepFormSchema),
    defaultValues: toFormValues(step),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(step));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the dialog opens or the source record changes
  }, [open, step]);

  const stepType = form.watch("step_type");
  const contentSource = form.watch("content_source");

  async function onSubmit(values: SequenceStepFormValues): Promise<void> {
    const condition = values.skip_if ? { skip_if: values.skip_if } : undefined;
    const payload = {
      step_type: values.step_type,
      delay_days: values.delay_days,
      delay_hours: values.delay_hours,
      content_source: values.step_type === "email" ? values.content_source : undefined,
      email_template_id:
        values.step_type === "email" && values.content_source === "template" ? values.email_template_id || undefined : undefined,
      subject_override: values.subject_override || undefined,
      body_override: values.body_override || undefined,
      condition,
    };

    try {
      if (isEditing && step) {
        await updateStep({ campaignId, stepId: step.id, payload });
      } else {
        await createStep({ campaignId, sequenceId, payload: { ...payload, step_order: nextStepOrder } });
      }
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit step" : "Add step"}</DialogTitle>
          <DialogDescription>
            {isEditing ? "Update this sequence step." : "Appends a new step to the end of the sequence."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form id="sequence-step-form" onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="step_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Step type</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {SUPPORTED_STEP_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {STEP_TYPE_LABELS[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="delay_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Delay (days)</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} max={365} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="delay_hours"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Delay (hours)</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} max={23} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {stepType === "email" && (
              <>
                <FormField
                  control={form.control}
                  name="content_source"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel required>Content source</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="template">Use a template</SelectItem>
                          <SelectItem value="ai_personalized">AI-generate per lead</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {contentSource === "template" && (
                  <FormField
                    control={form.control}
                    name="email_template_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel required>Template</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select a template" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {templates.map((template) => (
                              <SelectItem key={template.id} value={template.id}>
                                {template.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                <FormField
                  control={form.control}
                  name="subject_override"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Subject override</FormLabel>
                      <FormControl>
                        <Input placeholder="Leave blank to use the template subject" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="body_override"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Body override</FormLabel>
                      <FormControl>
                        <Textarea rows={3} placeholder="Leave blank to use the template body" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="skip_if"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Conditional skip</FormLabel>
                      <Select value={field.value || ""} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {SKIP_IF_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}
          </form>
        </Form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="sequence-step-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Add step"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
