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
import { Input } from "@/components/ui/input";
import { authService } from "@/features/auth/services/auth.service";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "../schemas";

export interface ForgotPasswordFormProps {
  onSuccess: (email: string) => void;
}

/**
 * Wired to `POST /auth/forgot-password`. The backend always returns the same
 * success response whether or not the email exists (account-enumeration
 * protection) — so this form has exactly one success state, never a
 * "no account found" error.
 */
export function ForgotPasswordForm({ onSuccess }: ForgotPasswordFormProps): React.ReactElement {
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotPasswordFormValues): Promise<void> {
    setFormError(null);
    try {
      await authService.forgotPassword(values);
      onSuccess(values.email);
    } catch (error) {
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
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Email</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="email" placeholder="you@company.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" fullWidth isLoading={form.formState.isSubmitting}>
          Send reset link
        </Button>
      </form>
    </Form>
  );
}
