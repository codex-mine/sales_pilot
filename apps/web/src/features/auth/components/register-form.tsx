"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { AlertCircle } from "@/icons";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { PasswordInput } from "@/components/ui/password-input";
import { useAuthStore } from "@/store/auth-store";
import { authService } from "@/features/auth/services/auth.service";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { registerSchema, type RegisterFormValues } from "../schemas";

export interface RegisterFormProps {
  /** Called after a successful registration + auto-login, with the email that was registered (for the "verify your email" follow-up screen). */
  onSuccess: (email: string) => void;
}

/**
 * Wired to `POST /auth/register`. Registration also creates the
 * organization/workspace (via `organization_name`) and logs the new owner in
 * immediately — the backend issues session cookies in the same response, so
 * we just refresh the store from `/auth/me` afterward, same as login.
 */
export function RegisterForm({ onSuccess }: RegisterFormProps): React.ReactElement {
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      organization_name: "",
      password: "",
      confirm_password: "",
    },
  });

  async function onSubmit(values: RegisterFormValues): Promise<void> {
    setFormError(null);
    try {
      await authService.register({
        email: values.email,
        password: values.password,
        first_name: values.first_name,
        last_name: values.last_name,
        organization_name: values.organization_name,
      });
      // Registration auto-logs-in server-side (cookies are already set) —
      // populate the store the same way `login()` does.
      await useAuthStore.getState().loadUser();
      useAuthStore.setState({ isInitialized: true });
      onSuccess(values.email);
    } catch (error) {
      const message = applyServerErrors(error, form.setError);
      if (message) setFormError(message);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-5">
        {formError && (
          <Alert variant="danger" icon={AlertCircle}>
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="first_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel required>First name</FormLabel>
                <FormControl>
                  <Input autoComplete="given-name" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="last_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel required>Last name</FormLabel>
                <FormControl>
                  <Input autoComplete="family-name" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Work email</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="email" placeholder="you@company.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="organization_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Workspace name</FormLabel>
              <FormControl>
                <Input autoComplete="organization" placeholder="Acme Inc" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Password</FormLabel>
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
              <FormLabel required>Confirm password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" fullWidth isLoading={form.formState.isSubmitting}>
          Create workspace
        </Button>
      </form>
    </Form>
  );
}
