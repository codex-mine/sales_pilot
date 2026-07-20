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
import { Switch } from "@/components/ui/switch";
import { TagInput } from "@/components/ui/tag-input";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreateReport, useUpdateReport } from "../hooks/use-report-mutations";
import { reportFormSchema, type ReportFormValues } from "../schemas";
import {
  DATE_RANGE_LABELS,
  DATE_RANGE_PRESETS,
  REPORT_TYPE_CHOICES,
  REPORT_TYPE_LABELS,
  SCHEDULE_CADENCE_CHOICES,
  type ReportResponse,
} from "../types";

export interface ReportFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  report?: ReportResponse;
}

function toFormValues(report?: ReportResponse): ReportFormValues {
  return {
    name: report?.name ?? "",
    report_type: (report?.report_type as ReportFormValues["report_type"]) ?? "pipeline",
    date_range: (report?.config?.date_range as ReportFormValues["date_range"]) ?? "last_30_days",
    is_scheduled: report?.is_scheduled ?? false,
    schedule_cron: (report?.schedule_cron as ReportFormValues["schedule_cron"]) ?? undefined,
    recipients: report?.recipients ?? [],
  };
}

export function ReportFormDialog({ open, onOpenChange, report }: ReportFormDialogProps): React.ReactElement {
  const isEditing = Boolean(report);
  const { createReport, isCreating } = useCreateReport();
  const { updateReport, isUpdating } = useUpdateReport();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<ReportFormValues>({
    resolver: zodResolver(reportFormSchema),
    defaultValues: toFormValues(report),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(report));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the dialog opens or the source record changes
  }, [open, report]);

  const isScheduled = form.watch("is_scheduled");

  async function onSubmit(values: ReportFormValues): Promise<void> {
    const payload = {
      name: values.name,
      report_type: values.report_type,
      config: { date_range: values.date_range },
      is_scheduled: values.is_scheduled,
      schedule_cron: values.is_scheduled ? values.schedule_cron : undefined,
      recipients: values.recipients.length ? values.recipients : undefined,
    };

    try {
      if (isEditing && report) {
        await updateReport({ reportId: report.id, payload });
      } else {
        await createReport(payload);
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
          <DialogTitle>{isEditing ? "Edit report" : "Create report"}</DialogTitle>
          <DialogDescription>
            {isEditing ? "Update this report's settings." : "Set up a saved report, optionally delivered on a schedule."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form id="report-form" onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Report name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="report_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Data source</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange} disabled={isEditing}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {REPORT_TYPE_CHOICES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {REPORT_TYPE_LABELS[type]}
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
              name="date_range"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Date range</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {DATE_RANGE_PRESETS.map((preset) => (
                        <SelectItem key={preset} value={preset}>
                          {DATE_RANGE_LABELS[preset]}
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
              name="recipients"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email recipients</FormLabel>
                  <FormControl>
                    <TagInput tags={field.value} onTagsChange={field.onChange} placeholder="Add an email..." />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_scheduled"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border border-border p-4">
                  <div className="flex flex-col gap-1">
                    <FormLabel className="text-body-sm font-medium">Recurring delivery</FormLabel>
                    <p className="text-caption text-muted-foreground">
                      Automatically run and email this report to its recipients on a schedule.
                    </p>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />

            {isScheduled && (
              <FormField
                control={form.control}
                name="schedule_cron"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Cadence</FormLabel>
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a cadence" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {SCHEDULE_CADENCE_CHOICES.map((cadence) => (
                          <SelectItem key={cadence} value={cadence}>
                            {cadence.charAt(0).toUpperCase() + cadence.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
          </form>
        </Form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="report-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Create report"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
