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
import { MultiSelect, type MultiSelectOption } from "@/components/ui/multi-select";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { getInitials } from "@/lib/utils";
import { useCreateCampaign, useUpdateCampaign } from "../hooks/use-campaign-mutations";
import { campaignFormSchema, type CampaignFormValues } from "../schemas";
import { SEND_DAYS, type CampaignResponse } from "../types";

const SEND_DAY_OPTIONS: MultiSelectOption[] = SEND_DAYS.map((day) => ({
  value: day,
  label: day.charAt(0).toUpperCase() + day.slice(1),
}));

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${String(hour).padStart(2, "0")}:00`,
}));

export interface CampaignFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  campaign?: CampaignResponse;
}

function toFormValues(campaign?: CampaignResponse): CampaignFormValues {
  return {
    name: campaign?.name ?? "",
    description: campaign?.description ?? "",
    goal: campaign?.goal ?? "",
    target_industry: campaign?.target_industry ?? "",
    target_company_size: campaign?.target_company_size ?? "",
    target_job_titles: campaign?.target_job_titles ?? [],
    value_proposition: campaign?.value_proposition ?? "",
    daily_send_limit: campaign?.daily_send_limit ?? 50,
    timezone: campaign?.timezone ?? "UTC",
    send_days: campaign?.send_days ?? ["monday", "tuesday", "wednesday", "thursday", "friday"],
    send_start_hour: campaign?.send_start_hour ?? 9,
    send_end_hour: campaign?.send_end_hour ?? 17,
    owner_id: campaign?.owner?.id ?? "",
    requires_approval: campaign?.requires_approval ?? true,
  };
}

/** Shared create/edit form — same fields, same validation, different submit action. */
export function CampaignFormDrawer({ open, onOpenChange, campaign }: CampaignFormDrawerProps): React.ReactElement {
  const isEditing = Boolean(campaign);
  const { createCampaign, isCreating } = useCreateCampaign();
  const { updateCampaign, isUpdating } = useUpdateCampaign();
  const { members } = useOrganizationMembers();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignFormSchema),
    defaultValues: toFormValues(campaign),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(campaign));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the drawer opens or the source record changes
  }, [open, campaign]);

  async function onSubmit(values: CampaignFormValues): Promise<void> {
    const payload = {
      name: values.name,
      description: values.description || undefined,
      goal: values.goal || undefined,
      target_industry: values.target_industry || undefined,
      target_company_size: values.target_company_size || undefined,
      target_job_titles: values.target_job_titles.length ? values.target_job_titles : undefined,
      value_proposition: values.value_proposition || undefined,
      daily_send_limit: values.daily_send_limit,
      timezone: values.timezone,
      send_days: values.send_days,
      send_start_hour: values.send_start_hour,
      send_end_hour: values.send_end_hour,
      owner_id: values.owner_id || undefined,
      requires_approval: values.requires_approval,
    };

    try {
      if (isEditing && campaign) {
        await updateCampaign({ campaignId: campaign.id, payload });
      } else {
        await createCampaign(payload);
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
          <DrawerTitle>{isEditing ? "Edit campaign" : "Create campaign"}</DrawerTitle>
          <DrawerDescription>
            {isEditing
              ? "Update this campaign's targeting and send settings."
              : "Set up a new outbound campaign. Add a sequence and enroll leads once it's created."}
          </DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form
            id="campaign-form"
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-1 flex-col gap-4 overflow-y-auto"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required>Campaign name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="goal"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Goal</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Book 10 demos this quarter" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="value_proposition"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Value proposition</FormLabel>
                  <FormControl>
                    <Textarea rows={2} placeholder="What's the pitch this campaign is built around?" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="target_industry"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Target industry</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="target_company_size"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Target company size</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. 50-200" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="target_job_titles"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Target job titles</FormLabel>
                  <FormControl>
                    <TagInput tags={field.value} onTagsChange={field.onChange} placeholder="Add a job title..." />
                  </FormControl>
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

            <div className="flex flex-col gap-4 rounded-lg border border-border p-4">
              <p className="text-body-sm font-medium text-foreground">Send window</p>
              <FormField
                control={form.control}
                name="send_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Send days</FormLabel>
                    <FormControl>
                      <MultiSelect options={SEND_DAY_OPTIONS} values={field.value} onValuesChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <FormField
                  control={form.control}
                  name="send_start_hour"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Start hour</FormLabel>
                      <Select value={String(field.value)} onValueChange={(v) => field.onChange(Number(v))}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {HOUR_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
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
                  name="send_end_hour"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>End hour</FormLabel>
                      <Select value={String(field.value)} onValueChange={(v) => field.onChange(Number(v))}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {HOUR_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
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
                  name="daily_send_limit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Daily limit</FormLabel>
                      <FormControl>
                        <Input type="number" min={1} max={2000} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timezone</FormLabel>
                    <FormControl>
                      <Input placeholder="UTC" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="requires_approval"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border border-border p-4">
                  <div className="flex flex-col gap-1">
                    <FormLabel className="text-body-sm font-medium">Require approval before sending</FormLabel>
                    <p className="text-caption text-muted-foreground">
                      Sequence emails wait as drafts for a human to approve. Turn off for full automation.
                    </p>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
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
          <Button type="submit" form="campaign-form" isLoading={isSubmitting}>
            {isEditing ? "Save changes" : "Create campaign"}
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
