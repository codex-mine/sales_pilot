"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useOrganizationMembers } from "@/features/organizations/hooks/use-organization-members";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { getInitials } from "@/lib/utils";
import { useCreateCompany, useUpdateCompany } from "../hooks/use-company-mutations";
import { companyFormSchema, type CompanyFormValues } from "../schemas";
import { COMPANY_SIZE_CHOICES, COMPANY_STATUS_CHOICES, COMPANY_STATUS_LABELS, type CompanyResponse } from "../types";

export interface CompanyFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  company?: CompanyResponse;
}

function toFormValues(company?: CompanyResponse): CompanyFormValues {
  return {
    name: company?.name ?? "",
    legal_name: company?.legal_name ?? "",
    website: company?.website ?? "",
    industry: company?.industry ?? "",
    description: company?.description ?? "",
    phone: company?.phone ?? "",
    email: company?.email ?? "",
    founded_year: company?.founded_year ?? "",
    size_range: company?.size_range ?? "",
    annual_revenue: company?.annual_revenue ?? "",
    currency: company?.currency ?? "USD",
    country: company?.country ?? "",
    state: company?.state ?? "",
    city: company?.city ?? "",
    postal_code: company?.postal_code ?? "",
    address_line1: company?.address?.line1 ?? "",
    address_line2: company?.address?.line2 ?? "",
    linkedin_url: company?.linkedin_url ?? "",
    twitter_url: company?.twitter_url ?? "",
    facebook_url: company?.facebook_url ?? "",
    instagram_url: company?.instagram_url ?? "",
    status: (company?.status as CompanyFormValues["status"]) ?? "prospect",
    owner_id: company?.owner?.id ?? "",
    tags: company?.tags.map((t) => t.name) ?? [],
  };
}

/** Shared create/edit form — same fields, same validation, different submit action. */
export function CompanyFormDrawer({ open, onOpenChange, company }: CompanyFormDrawerProps): React.ReactElement {
  const isEditing = Boolean(company);
  const { createCompany, isCreating } = useCreateCompany();
  const { updateCompany, isUpdating } = useUpdateCompany();
  const { members } = useOrganizationMembers();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companyFormSchema),
    defaultValues: toFormValues(company),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(company));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, company]);

  async function onSubmit(values: CompanyFormValues): Promise<void> {
    const payload = {
      name: values.name,
      legal_name: values.legal_name || undefined,
      website: values.website || undefined,
      industry: values.industry || undefined,
      description: values.description || undefined,
      phone: values.phone || undefined,
      email: values.email || undefined,
      founded_year: values.founded_year === "" ? undefined : values.founded_year,
      size_range: values.size_range || undefined,
      annual_revenue: values.annual_revenue === "" ? undefined : values.annual_revenue,
      currency: values.currency || "USD",
      country: values.country || undefined,
      state: values.state || undefined,
      city: values.city || undefined,
      postal_code: values.postal_code || undefined,
      address:
        values.address_line1 || values.address_line2
          ? { line1: values.address_line1 || undefined, line2: values.address_line2 || undefined }
          : undefined,
      linkedin_url: values.linkedin_url || undefined,
      twitter_url: values.twitter_url || undefined,
      facebook_url: values.facebook_url || undefined,
      instagram_url: values.instagram_url || undefined,
      status: values.status,
      owner_id: values.owner_id || undefined,
      tags: values.tags,
    };

    try {
      if (isEditing && company) {
        await updateCompany({ companyId: company.id, payload });
      } else {
        await createCompany(payload);
      }
      onOpenChange(false);
    } catch (error) {
      applyServerErrors(error, form.setError);
    }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-w-lg">
        <DrawerHeader>
          <DrawerTitle>{isEditing ? "Edit company" : "Create company"}</DrawerTitle>
          <DrawerDescription>
            {isEditing ? "Update this company's information." : "Add a new company to your CRM."}
          </DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form
            id="company-form"
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-1 flex-col gap-4 overflow-y-auto"
          >
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Company name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="legal_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Legal name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="hello@company.com" {...field} />
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
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Status</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {COMPANY_STATUS_CHOICES.map((status) => (
                          <SelectItem key={status} value={status}>
                            {COMPANY_STATUS_LABELS[status]}
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
                name="owner_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Owner</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Unassigned" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {members.map((member) => (
                          <SelectItem key={member.id} value={member.id}>
                            <div className="flex items-center gap-2">
                              <Avatar size="xs" fallback={getInitials(member.full_name)} />
                              {member.full_name}
                            </div>
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
              name="tags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tags</FormLabel>
                  <FormControl>
                    <TagInput tags={field.value} onTagsChange={field.onChange} placeholder="Add a tag..." />
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
                name="linkedin_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>LinkedIn</FormLabel>
                    <FormControl>
                      <Input placeholder="https://linkedin.com/company/..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="twitter_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Twitter / X</FormLabel>
                    <FormControl>
                      <Input placeholder="https://x.com/..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="facebook_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Facebook</FormLabel>
                    <FormControl>
                      <Input placeholder="https://facebook.com/..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="instagram_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Instagram</FormLabel>
                    <FormControl>
                      <Input placeholder="https://instagram.com/..." {...field} />
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
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="size_range"
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
                        {COMPANY_SIZE_CHOICES.map((size) => (
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
            </div>
            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="founded_year"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Founded year</FormLabel>
                    <FormControl>
                      <Input type="number" min={1800} max={2100} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="annual_revenue"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Annual revenue</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Currency</FormLabel>
                    <FormControl>
                      <Input maxLength={3} placeholder="USD" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="city"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>City</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="state"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>State</FormLabel>
                    <FormControl>
                      <Input {...field} />
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
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="address_line1"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address line 1</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="postal_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Postal code</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea rows={3} {...field} />
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
          <Button type="submit" form="company-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Create company"}
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
