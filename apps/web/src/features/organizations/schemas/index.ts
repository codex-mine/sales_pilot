import { z } from "zod";
import { passwordSchema } from "@/features/auth/schemas";

export const inviteUserSchema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
  role_id: z.string().min(1, "Select a role."),
});
export type InviteUserFormValues = z.infer<typeof inviteUserSchema>;

export const acceptInvitationSchema = z
  .object({
    first_name: z.string().min(1, "First name is required.").max(100),
    last_name: z.string().min(1, "Last name is required.").max(100),
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });
export type AcceptInvitationFormValues = z.infer<typeof acceptInvitationSchema>;

// ─── Organization CRUD / settings ──────────────────────────────────────────────

const slugSchema = z
  .string()
  .min(1, "Slug is required.")
  .max(100)
  .regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "Use lowercase letters, numbers, and hyphens only.");

const optionalUrl = z
  .string()
  .trim()
  .refine((value) => value === "" || /^https?:\/\//.test(value), {
    message: "Website must start with http:// or https://.",
  })
  .optional()
  .or(z.literal(""));

/** "General" tab: identity + contact fields. Maps to `PATCH /organizations/{id}`. */
export const organizationDetailsSchema = z.object({
  name: z.string().min(1, "Organization name is required.").max(255),
  slug: slugSchema,
  website: optionalUrl,
  email: z.string().trim().email("Enter a valid email address.").optional().or(z.literal("")),
  phone: z.string().trim().max(50).optional().or(z.literal("")),
  industry: z.string().trim().max(100).optional().or(z.literal("")),
  country: z.string().trim().max(100).optional().or(z.literal("")),
  company_size: z.string().optional().or(z.literal("")),
  description: z.string().trim().max(2000).optional().or(z.literal("")),
});
export type OrganizationDetailsFormValues = z.infer<typeof organizationDetailsSchema>;

/** "Settings" tab: regional/branding fields, editable independently of profile info. */
export const organizationSettingsSchema = z.object({
  timezone: z.string().min(1, "Select a timezone."),
  language: z
    .string()
    .regex(/^[a-z]{2}(-[A-Z]{2})?$/, "Use a language code like 'en' or 'en-US'."),
  currency: z.string().regex(/^[A-Z]{3}$/, "Use a 3-letter currency code like 'USD'."),
  brand_color: z
    .string()
    .regex(/^#[0-9A-Fa-f]{6}$/, "Enter a hex color like #16A34A.")
    .optional()
    .or(z.literal("")),
  address_line1: z.string().trim().max(255).optional().or(z.literal("")),
  address_line2: z.string().trim().max(255).optional().or(z.literal("")),
  address_city: z.string().trim().max(100).optional().or(z.literal("")),
  address_state: z.string().trim().max(100).optional().or(z.literal("")),
  address_postal_code: z.string().trim().max(20).optional().or(z.literal("")),
});
export type OrganizationSettingsFormValues = z.infer<typeof organizationSettingsSchema>;
