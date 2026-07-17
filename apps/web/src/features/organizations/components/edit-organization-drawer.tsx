"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Pencil } from "@/icons";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
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
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useUpdateOrganization } from "../hooks/use-update-organization";
import { organizationDetailsSchema, type OrganizationDetailsFormValues } from "../schemas";
import { COMPANY_SIZES, type OrganizationDetailResponse } from "../types";

export interface EditOrganizationDrawerProps {
  organization: OrganizationDetailResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** RHF+Zod form for the organization's identity/contact fields — name, slug, website, email, phone, industry, country, company size, description. Settings (timezone/currency/etc.) live in a separate, independently-saved form (see organization-settings-form.tsx). */
export function EditOrganizationDrawer({
  organization,
  open,
  onOpenChange,
}: EditOrganizationDrawerProps): React.ReactElement {
  const { updateOrganization, isUpdating } = useUpdateOrganization();

  const form = useForm<OrganizationDetailsFormValues>({
    resolver: zodResolver(organizationDetailsSchema),
    defaultValues: toFormValues(organization),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(organization));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, organization]);

  async function onSubmit(values: OrganizationDetailsFormValues): Promise<void> {
    try {
      await updateOrganization({
        name: values.name,
        slug: values.slug,
        website: values.website || null,
        email: values.email || null,
        phone: values.phone || null,
        industry: values.industry || null,
        country: values.country || null,
        company_size: values.company_size || null,
        description: values.description || null,
      });
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerTrigger asChild>
        <Button variant="outline" size="sm">
          <Pencil className="size-4" />
          Edit organization
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Edit organization</DrawerTitle>
          <DrawerDescription>Update your organization&apos;s profile information.</DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form
            id="edit-organization-form"
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-1 flex-col gap-4 overflow-y-auto"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Organization name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="slug"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>URL slug</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="website"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Website</FormLabel>
                  <FormControl>
                    <Input placeholder="https://example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Contact email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="hello@example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl>
                      <Input placeholder="+1 555 0100" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="industry"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Industry</FormLabel>
                    <FormControl>
                      <Input placeholder="Software" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="country"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Country</FormLabel>
                    <FormControl>
                      <Input placeholder="United States" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="company_size"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Company size</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a size" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {COMPANY_SIZES.map((size) => (
                        <SelectItem key={size} value={size}>
                          {size} employees
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
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea rows={4} placeholder="What does your team do?" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DrawerFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="edit-organization-form" isLoading={isUpdating}>
            Save changes
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}

function toFormValues(organization: OrganizationDetailResponse): OrganizationDetailsFormValues {
  return {
    name: organization.name,
    slug: organization.slug,
    website: organization.website ?? "",
    email: organization.email ?? "",
    phone: organization.phone ?? "",
    industry: organization.industry ?? "",
    country: organization.country ?? "",
    company_size: organization.company_size ?? "",
    description: organization.description ?? "",
  };
}
