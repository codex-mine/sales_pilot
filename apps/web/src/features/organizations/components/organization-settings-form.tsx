"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useUpdateOrganization } from "../hooks/use-update-organization";
import { organizationSettingsSchema, type OrganizationSettingsFormValues } from "../schemas";
import type { OrganizationDetailResponse } from "../types";

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "BRL", "MXN", "SGD"] as const;
const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "en-US", label: "English (US)" },
  { code: "en-GB", label: "English (UK)" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "pt", label: "Portuguese" },
  { code: "ja", label: "Japanese" },
  { code: "hi", label: "Hindi" },
];

function useTimezones(): string[] {
  return useMemo(() => {
    // `Intl.supportedValuesOf("timeZone")` omits the bare "UTC" zone (even
    // in full-ICU browsers) — but it's the backend's default for every new
    // organization, so it must always be a selectable option or that Select
    // renders blank for most orgs until someone explicitly picks a zone.
    try {
      return ["UTC", ...Intl.supportedValuesOf("timeZone")];
    } catch {
      return ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"];
    }
  }, []);
}

export interface OrganizationSettingsFormProps {
  organization: OrganizationDetailResponse;
}

/** Regional/branding settings — timezone, language, currency, brand color, address. Saved independently from the profile-details drawer (its own Save button, own mutation). */
export function OrganizationSettingsForm({
  organization,
}: OrganizationSettingsFormProps): React.ReactElement {
  const { updateOrganization, isUpdating } = useUpdateOrganization();
  const timezones = useTimezones();

  const form = useForm<OrganizationSettingsFormValues>({
    resolver: zodResolver(organizationSettingsSchema),
    defaultValues: {
      timezone: organization.timezone,
      language: organization.language,
      currency: organization.currency,
      brand_color: organization.brand_color ?? "",
      address_line1: organization.address?.line1 ?? "",
      address_line2: organization.address?.line2 ?? "",
      address_city: organization.address?.city ?? "",
      address_state: organization.address?.state ?? "",
      address_postal_code: organization.address?.postal_code ?? "",
    },
  });

  async function onSubmit(values: OrganizationSettingsFormValues): Promise<void> {
    try {
      await updateOrganization({
        timezone: values.timezone,
        language: values.language,
        currency: values.currency,
        brand_color: values.brand_color || null,
        address: {
          line1: values.address_line1 || null,
          line2: values.address_line2 || null,
          city: values.address_city || null,
          state: values.address_state || null,
          postal_code: values.address_postal_code || null,
        },
      });
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Regional & branding settings</CardTitle>
        <CardDescription>Timezone, language, currency, and brand color for your workspace.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Timezone</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select timezone" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="max-h-72">
                        {timezones.map((tz) => (
                          <SelectItem key={tz} value={tz}>
                            {tz}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="language"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Language</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang.code} value={lang.code}>
                            {lang.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Currency</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select currency" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {CURRENCIES.map((currency) => (
                          <SelectItem key={currency} value={currency}>
                            {currency}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="brand_color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Brand color</FormLabel>
                  <FormControl>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={field.value || "#16A34A"}
                        onChange={(event) => field.onChange(event.target.value)}
                        className="size-9 shrink-0 cursor-pointer rounded-md border border-input bg-card p-1"
                        aria-label="Pick brand color"
                      />
                      <Input placeholder="#16A34A" {...field} className="max-w-40" />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="address_line1"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Address line 1</FormLabel>
                    <FormControl>
                      <Input placeholder="1 Infinite Loop" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="address_line2"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Address line 2</FormLabel>
                    <FormControl>
                      <Input placeholder="Suite 100" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="address_city"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>City</FormLabel>
                    <FormControl>
                      <Input placeholder="Cupertino" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="address_state"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>State / Province</FormLabel>
                    <FormControl>
                      <Input placeholder="CA" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="address_postal_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Postal code</FormLabel>
                    <FormControl>
                      <Input placeholder="95014" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div>
              <Button type="submit" isLoading={isUpdating}>
                Save settings
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
