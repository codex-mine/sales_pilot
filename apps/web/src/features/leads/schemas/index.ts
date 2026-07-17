import { z } from "zod";
import { LEAD_STATUS_CHOICES } from "../types";

const optionalUrl = z
  .string()
  .trim()
  .refine((value) => value === "" || /^https?:\/\//.test(value), {
    message: "Must start with http:// or https://.",
  })
  .optional()
  .or(z.literal(""));

const optionalEmail = z.string().trim().email("Enter a valid email address.").optional().or(z.literal(""));

/** Create/edit lead form — every identity field is individually optional (a lead needs at least one), enforced by `_validate_lead_identity` below at submit time. */
export const leadFormSchema = z.object({
  first_name: z.string().trim().max(100).optional().or(z.literal("")),
  last_name: z.string().trim().max(100).optional().or(z.literal("")),
  email: optionalEmail,
  phone: z.string().trim().max(50).optional().or(z.literal("")),
  job_title: z.string().trim().max(255).optional().or(z.literal("")),
  company_name: z.string().trim().max(255).optional().or(z.literal("")),
  website: optionalUrl,
  industry: z.string().trim().max(100).optional().or(z.literal("")),
  source: z.string().optional().or(z.literal("")),
  status: z.enum(LEAD_STATUS_CHOICES),
  priority: z.coerce.number().min(0).max(100),
  country: z.string().trim().max(100).optional().or(z.literal("")),
  state: z.string().trim().max(100).optional().or(z.literal("")),
  city: z.string().trim().max(100).optional().or(z.literal("")),
  address_line1: z.string().trim().max(255).optional().or(z.literal("")),
  address_line2: z.string().trim().max(255).optional().or(z.literal("")),
  address_postal_code: z.string().trim().max(20).optional().or(z.literal("")),
  linkedin_url: optionalUrl,
  twitter_url: optionalUrl,
  company_size: z.string().optional().or(z.literal("")),
  // `z.literal("")` must come *before* `z.coerce.number()` in the union —
  // coercion runs first if it's tried first, and `Number("")` is `0`, so an
  // empty field would silently become 0 instead of staying empty.
  revenue: z.literal("").or(z.coerce.number().min(0)),
  employee_count: z.literal("").or(z.coerce.number().int().min(0)),
  owner_id: z.string().optional().or(z.literal("")),
  tags: z.array(z.string()).default([]),
  description: z.string().trim().max(5000).optional().or(z.literal("")),
  lead_score: z.literal("").or(z.coerce.number().min(0).max(100)),
});
export type LeadFormValues = z.infer<typeof leadFormSchema>;

export function validateLeadIdentity(values: LeadFormValues): string | null {
  if (!values.first_name && !values.last_name && !values.email && !values.company_name) {
    return "Provide at least a name, email, or company.";
  }
  return null;
}

export const noteFormSchema = z.object({
  content: z.string().min(1, "Note can't be empty.").max(10_000),
  is_pinned: z.boolean().default(false),
});
export type NoteFormValues = z.infer<typeof noteFormSchema>;

export const importMappingSchema = z.object({
  mapping: z.record(z.string(), z.string()),
});
