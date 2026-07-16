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
import { PasswordInput } from "@/components/ui/password-input";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { normalizeApiError } from "@/lib/api/errors";
import { useAuthStore } from "@/store/auth-store";
import { organizationService } from "../services/organization.service";
import { acceptInvitationSchema, type AcceptInvitationFormValues } from "../schemas";

export interface AcceptInvitationFormProps {
  token: string;
  onSuccess: () => void;
  onInvalidToken: () => void;
}

/** Wired to `POST /organizations/invitations/accept`, which also auto-logs the new member in (sets session cookies). */
export function AcceptInvitationForm({
  token,
  onSuccess,
  onInvalidToken,
}: AcceptInvitationFormProps): React.ReactElement {
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<AcceptInvitationFormValues>({
    resolver: zodResolver(acceptInvitationSchema),
    defaultValues: { first_name: "", last_name: "", password: "", confirm_password: "" },
  });

  async function onSubmit(values: AcceptInvitationFormValues): Promise<void> {
    setFormError(null);
    try {
      await organizationService.acceptInvitation({
        token,
        first_name: values.first_name,
        last_name: values.last_name,
        password: values.password,
      });
      await useAuthStore.getState().loadUser();
      useAuthStore.setState({ isInitialized: true });
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

        <div className="grid grid-cols-2 gap-4">
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
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>Password</FormLabel>
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
              <FormLabel required>Confirm password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" fullWidth isLoading={form.formState.isSubmitting}>
          Join workspace
        </Button>
      </form>
    </Form>
  );
}
