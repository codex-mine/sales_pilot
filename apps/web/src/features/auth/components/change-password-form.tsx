"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
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
import { changePasswordSchema, type ChangePasswordFormValues } from "../schemas";

/** Wired to `POST /auth/change-password`. */
export function ChangePasswordForm(): React.ReactElement {
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  async function onSubmit(values: ChangePasswordFormValues): Promise<void> {
    setFormError(null);
    try {
      await authService.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success("Password changed.");
      form.reset();
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
          name="current_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Current password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="new_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>New password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" {...field} />
              </FormControl>
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

        <Button type="submit" className="self-start" isLoading={form.formState.isSubmitting}>
          Update password
        </Button>
      </form>
    </Form>
  );
}
