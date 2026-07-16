import { z } from "zod";

/**
 * Mirrors the backend's password policy exactly (`app.security.passwords.
 * validate_password_strength`): 8-128 chars, at least one upper/lower/digit/
 * special character. Client-side validation here is a UX nicety — the
 * backend re-validates and is the source of truth; see `extractFieldErrors`
 * for how a 422 from the server still surfaces on the right field.
 */
export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters long.")
  .max(128, "Password must be at most 128 characters long.")
  .regex(/[A-Z]/, "Password must contain at least one uppercase letter.")
  .regex(/[a-z]/, "Password must contain at least one lowercase letter.")
  .regex(/\d/, "Password must contain at least one number.")
  .regex(/[^A-Za-z0-9]/, "Password must contain at least one special character.");

export const loginSchema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
  remember_me: z.boolean().default(false),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    first_name: z.string().min(1, "First name is required.").max(100),
    last_name: z.string().min(1, "Last name is required.").max(100),
    email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
    organization_name: z.string().min(1, "Workspace name is required.").max(255),
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });
export type RegisterFormValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
});
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required."),
    new_password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your new password."),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  })
  .refine((data) => data.current_password !== data.new_password, {
    message: "New password must be different from your current password.",
    path: ["new_password"],
  });
export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;
