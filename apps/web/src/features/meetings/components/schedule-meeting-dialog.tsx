"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Check, Copy, Sparkles } from "@/icons";
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import { useCreateMeeting, useProposeTimes } from "../hooks/use-meeting-mutations";
import { scheduleMeetingFormSchema, type ScheduleMeetingFormValues } from "../schemas";

export interface ScheduleMeetingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadId: string;
  /** The originating reply this meeting was proposed from (module 09's
   * MEETING_REQUESTED handoff) — threaded through to `Meeting.notes` for
   * traceability. */
  sourceMessageId?: string;
  defaultTitle?: string;
}

/** "Schedule Meeting": creates the Meeting, immediately proposes times against
 * the owner's connected calendar, and surfaces the shareable booking link. */
export function ScheduleMeetingDialog({
  open,
  onOpenChange,
  leadId,
  sourceMessageId,
  defaultTitle = "Intro call",
}: ScheduleMeetingDialogProps): React.ReactElement {
  const { createMeeting, isCreating } = useCreateMeeting();
  const { proposeTimes, isProposing } = useProposeTimes();
  const { copied, copy } = useCopyToClipboard();
  const [bookingUrl, setBookingUrl] = useState<string | null>(null);

  const form = useForm<ScheduleMeetingFormValues>({
    resolver: zodResolver(scheduleMeetingFormSchema),
    defaultValues: { title: defaultTitle, duration_minutes: 30, description: "" },
  });

  const isSubmitting = isCreating || isProposing;

  async function onSubmit(values: ScheduleMeetingFormValues): Promise<void> {
    const meeting = await createMeeting({
      leadId,
      payload: {
        title: values.title, duration_minutes: values.duration_minutes,
        description: values.description || undefined, source_message_id: sourceMessageId,
      },
    });
    const result = await proposeTimes({ meetingId: meeting.id, leadId });
    setBookingUrl(result.booking_url);
  }

  function handleOpenChange(next: boolean): void {
    if (!next) {
      setBookingUrl(null);
      form.reset({ title: defaultTitle, duration_minutes: 30, description: "" });
    }
    onOpenChange(next);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        {bookingUrl ? (
          <>
            <DialogHeader>
              <DialogTitle>Times proposed</DialogTitle>
              <DialogDescription>
                Share this booking link with your lead — they can pick a time without needing an account.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-3">
              <span className="min-w-0 flex-1 truncate text-body-sm text-foreground">{bookingUrl}</span>
              <Button type="button" size="sm" variant="outline" onClick={() => void copy(bookingUrl)}>
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Schedule a meeting</DialogTitle>
              <DialogDescription>
                Creates the meeting and proposes open times from your connected Google Calendar.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="meeting-title">Title</Label>
                <Input id="meeting-title" {...form.register("title")} />
                {form.formState.errors.title && (
                  <p className="text-body-sm text-danger">{form.formState.errors.title.message}</p>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="meeting-duration">Duration (minutes)</Label>
                <Input id="meeting-duration" type="number" step={15} min={15} max={480} {...form.register("duration_minutes")} />
                {form.formState.errors.duration_minutes && (
                  <p className="text-body-sm text-danger">{form.formState.errors.duration_minutes.message}</p>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="meeting-description">Description (optional)</Label>
                <Textarea id="meeting-description" rows={3} {...form.register("description")} />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isSubmitting}>
                <Sparkles className="size-4" />
                Propose times
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
