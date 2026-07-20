import { z } from "zod";
import { DATE_RANGE_PRESETS, REPORT_TYPE_CHOICES, SCHEDULE_CADENCE_CHOICES } from "../types";

export const reportFormSchema = z
  .object({
    name: z.string().trim().min(1, "Report name is required.").max(255),
    report_type: z.enum(REPORT_TYPE_CHOICES),
    date_range: z.enum(DATE_RANGE_PRESETS).default("last_30_days"),
    is_scheduled: z.boolean().default(false),
    schedule_cron: z.enum(SCHEDULE_CADENCE_CHOICES).optional(),
    recipients: z.array(z.string().trim().email("Enter a valid email address.")).default([]),
  })
  .refine((values) => !values.is_scheduled || Boolean(values.schedule_cron), {
    message: "Choose a cadence for scheduled reports.",
    path: ["schedule_cron"],
  });
export type ReportFormValues = z.infer<typeof reportFormSchema>;
