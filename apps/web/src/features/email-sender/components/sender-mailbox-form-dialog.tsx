"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { PlugZap } from "@/icons";
import { applyServerErrors } from "@/lib/api/apply-server-errors";
import { useCreateSenderMailbox, useTestSmtpConnection, useUpdateSenderMailbox } from "../hooks/use-sender-mailboxes";
import { senderMailboxFormSchema, type SenderMailboxFormValues } from "../schemas";
import { ENCRYPTION_TYPE_CHOICES, ENCRYPTION_TYPE_LABELS, type SenderMailboxResponse } from "../types";

export interface SenderMailboxFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present for edit, absent for create. */
  mailbox?: SenderMailboxResponse;
}

function toFormValues(mailbox?: SenderMailboxResponse): SenderMailboxFormValues {
  return {
    name: mailbox?.name ?? "",
    email_address: mailbox?.email_address ?? "",
    host: mailbox?.host ?? "",
    port: mailbox?.port ?? 587,
    username: mailbox?.username ?? "",
    password: "",
    encryption_type: (mailbox?.encryption_type as SenderMailboxFormValues["encryption_type"]) ?? "starttls",
    from_name: mailbox?.from_name ?? "",
    reply_to: mailbox?.reply_to ?? "",
    is_default: mailbox?.is_default ?? false,
    daily_send_limit: mailbox?.daily_send_limit ?? "",
  };
}

/** Shared create/edit form. Both create and update run a real SMTP
 * connection test server-side before persisting (see
 * `EmailSenderSettingsService.create_mailbox`/`update_mailbox`) — the "Test
 * Connection" button here is purely for earlier, in-form feedback so a user
 * doesn't have to submit-and-fail to find out their credentials are wrong. */
export function SenderMailboxFormDialog({ open, onOpenChange, mailbox }: SenderMailboxFormDialogProps): React.ReactElement {
  const isEditing = Boolean(mailbox);
  const { createMailbox, isCreating } = useCreateSenderMailbox();
  const { updateMailbox, isUpdating } = useUpdateSenderMailbox();
  const { testConnection, isTesting } = useTestSmtpConnection();
  const isSubmitting = isCreating || isUpdating;

  const form = useForm<SenderMailboxFormValues>({
    resolver: zodResolver(senderMailboxFormSchema),
    defaultValues: toFormValues(mailbox),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(mailbox));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when the dialog opens or the source record changes
  }, [open, mailbox]);

  async function handleTestConnection(): Promise<void> {
    const values = form.getValues();
    if (!values.host || !values.password) {
      toast.error("Enter a host and password before testing.");
      return;
    }
    try {
      await testConnection({
        host: values.host, port: values.port, username: values.username || undefined,
        password: values.password, encryption_type: values.encryption_type,
      });
    } catch {
      // toasted by the hook's onError — nothing further to do here
    }
  }

  async function onSubmit(values: SenderMailboxFormValues): Promise<void> {
    try {
      if (isEditing && mailbox) {
        await updateMailbox({
          mailboxId: mailbox.id,
          payload: {
            name: values.name, email_address: values.email_address, host: values.host, port: values.port,
            username: values.username || undefined,
            password: values.password || undefined,
            encryption_type: values.encryption_type,
            from_name: values.from_name || undefined, reply_to: values.reply_to || undefined,
            daily_send_limit: values.daily_send_limit ? Number(values.daily_send_limit) : undefined,
          },
        });
      } else {
        if (!values.password) {
          form.setError("password", { message: "Password is required." });
          return;
        }
        await createMailbox({
          name: values.name, email_address: values.email_address, host: values.host, port: values.port,
          username: values.username || undefined, password: values.password,
          encryption_type: values.encryption_type,
          from_name: values.from_name || undefined, reply_to: values.reply_to || undefined,
          is_default: values.is_default,
          daily_send_limit: values.daily_send_limit ? Number(values.daily_send_limit) : undefined,
        });
      }
      onOpenChange(false);
    } catch (error) {
      // Connection-test failures surface as a 400 ValidationError with the
      // exact SMTP reason (no field-level `errors` dict) — when
      // `applyServerErrors` has nothing more specific to map, put it on the
      // password field (the most likely culprit) so it's actually visible.
      const fallbackMessage = applyServerErrors(error, form.setError);
      if (fallbackMessage) form.setError("password", { message: fallbackMessage });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit sender mailbox" : "Add sender mailbox"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update this mailbox's settings. Changing host/port/username/password/encryption re-verifies the connection before saving."
              : "Connects a real SMTP mailbox — the connection is verified before it's saved."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form id="sender-mailbox-form" onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Sales team" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="email_address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Email address</FormLabel>
                    <FormControl>
                      <Input placeholder="sales@example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="host"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel required>SMTP host</FormLabel>
                    <FormControl>
                      <Input placeholder="smtp.example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="port"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Port</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <Input {...field} />
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
                    <FormLabel required={!isEditing}>{isEditing ? "Password (leave blank to keep current)" : "Password"}</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="encryption_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>Encryption</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {ENCRYPTION_TYPE_CHOICES.map((type) => (
                          <SelectItem key={type} value={type}>
                            {ENCRYPTION_TYPE_LABELS[type]}
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
                    <FormLabel>Daily send limit</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="No limit" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="from_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>From name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Jane from Acme" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="reply_to"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Reply-To</FormLabel>
                    <FormControl>
                      <Input placeholder="Defaults to the mailbox address" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="is_default"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border border-border p-3">
                  <div>
                    <FormLabel className="text-body-sm font-medium">Default mailbox</FormLabel>
                    <p className="text-caption text-muted-foreground">Used for sends that don&apos;t pick a mailbox explicitly.</p>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} disabled={isEditing} />
                  </FormControl>
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DialogFooter className="sm:justify-between">
          <Button type="button" variant="outline" onClick={() => void handleTestConnection()} isLoading={isTesting}>
            <PlugZap className="size-4" />
            Test connection
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" form="sender-mailbox-form" isLoading={isSubmitting}>
              {isEditing ? "Save changes" : "Add mailbox"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
