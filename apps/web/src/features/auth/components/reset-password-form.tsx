"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { PasswordInput } from "@/components/ui/password-input";
import { authService } from "@/features/auth/services/auth.service";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { normalizeApiError } from "@/lib/api/errors";
import { resetPasswordSchema, type ResetPasswordFormValues } from "../schemas";

export interface ResetPasswordFormProps {
  token: string;
  onSuccess: () => void;
  /** Fired when the token itself is rejected (expired/invalid/already used) so the page can swap to an "expired link" state instead of a field error. */
  onInvalidToken: () => void;
}

/** Wired to `POST /auth/reset-password`. A successful reset revokes every existing session server-side, so the caller should redirect to `/login` afterward. */
export function ResetPasswordForm({
  token,
  onSuccess,
  onInvalidToken,
}: ResetPasswordFormProps): React.ReactElement {
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirm_password: "" },
  });

  async function onSubmit(values: ResetPasswordFormValues): Promise<void> {
    setFormError(null);
    try {
      await authService.resetPassword({ token, new_password: values.password });
      onSuccess();
    } catch (error) {
      const normalized = normalizeApiError(error);
      if (normalized.status === 401) {
        onInvalidToken();
        return;
      }
      const message = applyServerErrors(error, form.setError);
      if (message) setFormError(message);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-5">
        {formError && <p className="text-body-sm text-danger">{formError}</p>}

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>New password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" {...field} />
              </FormControl>
              <p className="text-caption text-muted-foreground">
                8+ characters, with upper &amp; lowercase letters, a number, and a special character.
              </p>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirm_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Confirm new password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" fullWidth isLoading={form.formState.isSubmitting}>
          Reset password
        </Button>
      </form>
    </Form>
  );
}
