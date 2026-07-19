import { z } from "zod";

export const campaignFormSchema = z
  .object({
    name: z.string().trim().min(1, "Campaign name is required.").max(255),
    description: z.string().trim().max(5000).optional().or(z.literal("")),
    goal: z.string().trim().max(512).optional().or(z.literal("")),
    target_industry: z.string().trim().max(100).optional().or(z.literal("")),
    target_company_size: z.string().trim().max(50).optional().or(z.literal("")),
    target_job_titles: z.array(z.string()).default([]),
    value_proposition: z.string().trim().optional().or(z.literal("")),
    daily_send_limit: z.coerce.number().int().min(1).max(2000).default(50),
    timezone: z.string().trim().min(1).max(50).default("UTC"),
    send_days: z.array(z.string()).min(1, "Select at least one send day."),
    send_start_hour: z.coerce.number().int().min(0).max(23),
    send_end_hour: z.coerce.number().int().min(0).max(23),
    owner_id: z.string().optional().or(z.literal("")),
    requires_approval: z.boolean().default(true),
  })
  .refine((values) => values.send_end_hour > values.send_start_hour, {
    message: "Send end hour must be after the start hour.",
    path: ["send_end_hour"],
  });
export type CampaignFormValues = z.infer<typeof campaignFormSchema>;

export const sequenceStepFormSchema = z
  .object({
    step_type: z.enum(["email", "wait", "task"]),
    delay_days: z.coerce.number().int().min(0).max(365).default(0),
    delay_hours: z.coerce.number().int().min(0).max(23).default(0),
    content_source: z.enum(["template", "ai_personalized"]).default("template"),
    email_template_id: z.string().optional().or(z.literal("")),
    subject_override: z.string().trim().max(512).optional().or(z.literal("")),
    body_override: z.string().optional().or(z.literal("")),
    skip_if: z.string().optional().or(z.literal("")),
  })
  .refine(
    (values) => values.step_type !== "email" || values.content_source !== "template" || Boolean(values.email_template_id),
    { message: "Choose a template.", path: ["email_template_id"] },
  );
export type SequenceStepFormValues = z.infer<typeof sequenceStepFormSchema>;
