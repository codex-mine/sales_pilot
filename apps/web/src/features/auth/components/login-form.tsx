"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { AlertCircle } from "@/icons";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { useAuth } from "@/features/auth/hooks/use-auth";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { loginSchema, type LoginFormValues } from "../schemas";

/** Wired to `POST /auth/login`, followed by `GET /auth/me` (see the auth store's `login()`). Redirect-on-success is handled by `<GuestGuard>` reacting to `isAuthenticated`. */
export function LoginForm(): React.ReactElement {
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", remember_me: false },
  });

  async function onSubmit(values: LoginFormValues): Promise<void> {
    setFormError(null);
    try {
      await login(values);
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

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center justify-between">
                <FormLabel required>Password</FormLabel>
                <Link href="/forgot-password" className="text-body-sm text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>
              <FormControl>
                <PasswordInput autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="remember_me"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center gap-2 space-y-0">
              <FormControl>
                <Checkbox checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
              <FormLabel className="cursor-pointer font-normal">Remember me for 30 days</FormLabel>
            </FormItem>
          )}
        />

        <Button type="submit" fullWidth isLoading={form.formState.isSubmitting}>
          Sign in
        </Button>
      </form>
    </Form>
  );
}
