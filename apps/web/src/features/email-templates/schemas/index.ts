import { z } from "zod";
import { EMAIL_TEMPLATE_TYPE_CHOICES, EMAIL_TONE_CHOICES } from "../types";

export const emailTemplateEditSchema = z.object({
  name: z.string().min(1, "Name is required.").max(255),
  template_type: z.enum(EMAIL_TEMPLATE_TYPE_CHOICES),
  tone: z.enum(EMAIL_TONE_CHOICES).optional(),
  subject: z.string().min(1, "Subject is required.").max(512),
  body_html: z.string().min(1, "Body is required."),
  body_text: z.string().optional(),
  variables_used: z.array(z.string()).default([]),
  is_active: z.boolean(),
});

export type EmailTemplateEditValues = z.infer<typeof emailTemplateEditSchema>;
