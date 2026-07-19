import { z } from "zod";

export const scheduleMeetingFormSchema = z.object({
  title: z.string().trim().min(1, "Title is required.").max(512),
  duration_minutes: z.coerce.number().min(15).max(480),
  description: z.string().trim().max(5000).optional().or(z.literal("")),
});
export type ScheduleMeetingFormValues = z.infer<typeof scheduleMeetingFormSchema>;

export const rescheduleMeetingFormSchema = z
  .object({
    new_start: z.string().min(1, "Start time is required."),
    new_end: z.string().min(1, "End time is required."),
  })
  .refine((values) => new Date(values.new_end) > new Date(values.new_start), {
    message: "End time must be after start time.",
    path: ["new_end"],
  });
export type RescheduleMeetingFormValues = z.infer<typeof rescheduleMeetingFormSchema>;

export const cancelMeetingFormSchema = z.object({
  reason: z.string().trim().max(1000).optional().or(z.literal("")),
});
export type CancelMeetingFormValues = z.infer<typeof cancelMeetingFormSchema>;

export const logOutcomeFormSchema = z.object({
  status: z.enum(["completed", "no_show"]),
  notes: z.string().trim().max(5000).optional().or(z.literal("")),
});
export type LogOutcomeFormValues = z.infer<typeof logOutcomeFormSchema>;
