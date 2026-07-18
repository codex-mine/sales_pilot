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
import { useUpdateEmailTemplate } from "../hooks/use-email-template-mutations";
import { emailTemplateEditSchema, type EmailTemplateEditValues } from "../schemas";
import {
  EMAIL_TEMPLATE_TYPE_CHOICES,
  EMAIL_TEMPLATE_TYPE_LABELS,
  EMAIL_TONE_CHOICES,
  EMAIL_TONE_LABELS,
  type EmailTemplateResponse,
} from "../types";

export interface EmailTemplateEditDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template: EmailTemplateResponse | undefined;
}

function toFormValues(template: EmailTemplateResponse | undefined): EmailTemplateEditValues {
  return {
    name: template?.name ?? "",
    template_type: (template?.template_type as EmailTemplateEditValues["template_type"]) ?? "cold_outreach",
    tone: (template?.tone as EmailTemplateEditValues["tone"]) ?? undefined,
    subject: template?.subject ?? "",
    body_html: template?.body_html ?? "",
    body_text: template?.body_text ?? "",
    is_active: template?.is_active ?? true,
  };
}

export function EmailTemplateEditDrawer({
  open,
  onOpenChange,
  template,
}: EmailTemplateEditDrawerProps): React.ReactElement {
  const { updateTemplate, isUpdating } = useUpdateEmailTemplate();

  const form = useForm<EmailTemplateEditValues>({
    resolver: zodResolver(emailTemplateEditSchema),
    defaultValues: toFormValues(template),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(template));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, template]);

  async function onSubmit(values: EmailTemplateEditValues): Promise<void> {
    if (!template) return;
    try {
      await updateTemplate({
        templateId: template.id,
        payload: { ...values, body_text: values.body_text || undefined },
      });
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-w-lg">
        <DrawerHeader>
          <DrawerTitle>Edit email template</DrawerTitle>
          <DrawerDescription>Update this reusable template&apos;s content and settings.</DrawerDescription>
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
                    <FormLabel required>Type</FormLabel>
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
                    <Input {...field} />
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
                    <Textarea rows={10} {...field} />
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
          <Button type="submit" form="email-template-form" isLoading={isUpdating}>
            Save changes
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
