import { z } from "zod";
import { COMPANY_STATUS_CHOICES } from "../types";

const optionalUrl = z
  .string()
  .trim()
  .refine((value) => value === "" || /^https?:\/\//.test(value), {
    message: "Must start with http:// or https://.",
  })
  .optional()
  .or(z.literal(""));

const optionalEmail = z.string().trim().email("Enter a valid email address.").optional().or(z.literal(""));

export const companyFormSchema = z.object({
  name: z.string().trim().min(1, "Company name is required.").max(255),
  legal_name: z.string().trim().max(255).optional().or(z.literal("")),
  website: optionalUrl,
  industry: z.string().trim().max(100).optional().or(z.literal("")),
  description: z.string().trim().max(5000).optional().or(z.literal("")),
  phone: z.string().trim().max(50).optional().or(z.literal("")),
  email: optionalEmail,
  // `z.literal("")` must come *before* `z.coerce.number()` in the union —
  // coercion runs first if it's tried first, and `Number("")` is `0`, so an
  // empty field would silently become 0 instead of staying empty.
  founded_year: z.literal("").or(z.coerce.number().int().min(1800).max(2100)),
  size_range: z.string().optional().or(z.literal("")),
  annual_revenue: z.literal("").or(z.coerce.number().min(0)),
  currency: z.string().trim().length(3).default("USD"),
  country: z.string().trim().max(100).optional().or(z.literal("")),
  state: z.string().trim().max(100).optional().or(z.literal("")),
  city: z.string().trim().max(100).optional().or(z.literal("")),
  postal_code: z.string().trim().max(20).optional().or(z.literal("")),
  address_line1: z.string().trim().max(255).optional().or(z.literal("")),
  address_line2: z.string().trim().max(255).optional().or(z.literal("")),
  linkedin_url: optionalUrl,
  twitter_url: optionalUrl,
  facebook_url: optionalUrl,
  instagram_url: optionalUrl,
  status: z.enum(COMPANY_STATUS_CHOICES),
  owner_id: z.string().optional().or(z.literal("")),
  tags: z.array(z.string()).default([]),
});
export type CompanyFormValues = z.infer<typeof companyFormSchema>;

export const companyNoteFormSchema = z.object({
  content: z.string().min(1, "Note can't be empty.").max(10_000),
  is_pinned: z.boolean().default(false),
});
export type CompanyNoteFormValues = z.infer<typeof companyNoteFormSchema>;
