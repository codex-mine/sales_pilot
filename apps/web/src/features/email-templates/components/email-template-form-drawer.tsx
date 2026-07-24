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
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreateEmailTemplate, useUpdateEmailTemplate } from "../hooks/use-email-template-mutations";
import { emailTemplateEditSchema, type EmailTemplateEditValues } from "../schemas";
import {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateResponse,
} from "../types";

export interface EmailTemplateFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  template?: EmailTemplateResponse;
}

function toFormValues(template: EmailTemplateResponse | undefined): EmailTemplateEditValues {
  return {
    name: template?.name ?? "",
    template_type: (template?.template_type as EmailTemplateEditValues["template_type"]) ?? "cold_outreach",
    tone: (template?.tone as EmailTemplateEditValues["tone"]) ?? undefined,
    subject: template?.subject ?? "",
    body_html: template?.body_html ?? "",
    body_text: template?.body_text ?? "",
    variables_used: template?.variables_used ?? [],
    is_active: template?.is_active ?? true,
  };
}

/** Shared create/edit form — manual (non-AI) templates share the exact same
 * fields AI-generated ones do (see `EmailTemplate` model's own docstring:
 * "from a usage perspective they are identical"). No rich-text/WYSIWYG
 * editor exists in this codebase yet, so body content is edited as raw
 * HTML in a textarea, same as the AI-generated-template edit flow already
 * did — adding a new editor dependency for this form alone would be scope
 * beyond what was asked. */
export function EmailTemplateFormDrawer({ open, onOpenChange, template }: EmailTemplateFormDrawerProps): React.ReactElement {
  const isEditing = Boolean(template);
  const { createTemplate, isCreating } = useCreateEmailTemplate();
  const { updateTemplate, isUpdating } = useUpdateEmailTemplate();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<EmailTemplateEditValues>({
    resolver: zodResolver(emailTemplateEditSchema),
    defaultValues: toFormValues(template),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(template));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, template]);

  async function onSubmit(values: EmailTemplateEditValues): Promise<void> {
    try {
      if (isEditing && template) {
        await updateTemplate({
          templateId: template.id,
          payload: { ...values, body_text: values.body_text || undefined },
        });
      } else {
        await createTemplate({ ...values, body_text: values.body_text || undefined });
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
          <DrawerTitle>{isEditing ? "Edit email template" : "Create email template"}</DrawerTitle>
          <DrawerDescription>
            {isEditing
              ? "Update this reusable template's content and settings."
              : "Write a reusable template from scratch — no AI generation needed."}
          </DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form
            id="email-template-form"
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
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="template_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Category</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {EMAIL_TEMPLATE_TYPE_CHOICES.map((type) => (
                          <SelectItem key={type} value={type}>
                            {EMAIL_TEMPLATE_TYPE_LABELS[type]}
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
                name="tone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tone</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="No tone set" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {EMAIL_TONE_CHOICES.map((tone) => (
                          <SelectItem key={tone} value={tone}>
                            {EMAIL_TONE_LABELS[tone]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="subject"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Subject</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Quick question, {{ lead.first_name }}" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="body_html"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Body (HTML)</FormLabel>
                  <FormControl>
                    <Textarea rows={10} placeholder="<p>Hi {{ lead.first_name }},</p>" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="body_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Plain-text fallback</FormLabel>
                  <FormControl>
                    <Textarea rows={5} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="variables_used"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Variables used</FormLabel>
                  <FormControl>
                    <TagInput tags={field.value} onTagsChange={field.onChange} placeholder="e.g. lead.first_name" />
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
                  <FormLabel className="mb-0">Active</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DrawerFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="email-template-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Create template"}
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
