import { z } from "zod";
import { ENCRYPTION_TYPE_CHOICES } from "../types";

export const senderMailboxFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required.").max(255),
  email_address: z.string().trim().email("Enter a valid email address.").max(255),
  host: z.string().trim().min(1, "SMTP host is required.").max(255),
  port: z.coerce.number().int().min(1).max(65535).default(587),
  username: z.string().trim().max(255).optional().or(z.literal("")),
  // Optional on edit (blank = keep the existing password) — required on
  // create, enforced by CreateSenderMailboxRequest requiring it separately.
  password: z.string().max(512).optional().or(z.literal("")),
  encryption_type: z.enum(ENCRYPTION_TYPE_CHOICES).default("starttls"),
  from_name: z.string().trim().max(255).optional().or(z.literal("")),
  reply_to: z.string().trim().email("Enter a valid email address.").max(255).optional().or(z.literal("")),
  is_default: z.boolean().default(false),
  daily_send_limit: z.coerce.number().int().min(1).max(10_000).optional().or(z.literal("")),
});
export type SenderMailboxFormValues = z.infer<typeof senderMailboxFormSchema>;
