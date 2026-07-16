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
