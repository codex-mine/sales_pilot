"use client";

import { format } from "date-fns";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CalendarDays, CheckCircle2, ExternalLink, XCircle } from "@/icons";
import { useCancelMeeting, useLogMeetingOutcome, useRescheduleMeeting } from "../hooks/use-meeting-mutations";
import type { MeetingResponse } from "../types";
import { MeetingStatusBadge } from "./meeting-status-badge";

export interface MeetingDetailDrawerProps {
  meeting: MeetingResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type Mode = "view" | "reschedule" | "outcome";

function toLocalInputValue(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function MeetingDetailDrawer({ meeting, open, onOpenChange }: MeetingDetailDrawerProps): React.ReactElement {
  const [mode, setMode] = useState<Mode>("view");
  const [newStart, setNewStart] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [outcomeStatus, setOutcomeStatus] = useState<"completed" | "no_show">("completed");
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  const { rescheduleMeeting, isRescheduling } = useRescheduleMeeting();
  const { cancelMeeting, isCancelling } = useCancelMeeting();
  const { logMeetingOutcome, isLogging } = useLogMeetingOutcome();
  const cancelConfirm = useConfirmDialog();

  function resetLocalState(): void {
    setMode("view");
    setNewStart("");
    setNewEnd("");
    setOutcomeNotes("");
    setCancelReason("");
  }

  function handleOpenChange(next: boolean): void {
    if (!next) resetLocalState();
    onOpenChange(next);
  }

  if (!meeting) return <Drawer open={open} onOpenChange={handleOpenChange} />;

  const canReschedule = meeting.status === "confirmed";
  const canCancel = meeting.status === "proposed" || meeting.status === "confirmed";
  const canLogOutcome = meeting.status === "confirmed" && meeting.scheduled_start && new Date(meeting.scheduled_start) < new Date();

  async function handleReschedule(): Promise<void> {
    if (!newStart || !newEnd) return;
    await rescheduleMeeting({
      meetingId: meeting!.id, leadId: meeting!.lead_id,
      payload: { new_start: new Date(newStart).toISOString(), new_end: new Date(newEnd).toISOString() },
    });
    resetLocalState();
  }

  async function handleCancel(): Promise<void> {
    await cancelMeeting({ meetingId: meeting!.id, leadId: meeting!.lead_id, payload: { reason: cancelReason || undefined } });
    cancelConfirm.close();
    resetLocalState();
    handleOpenChange(false);
  }

  async function handleLogOutcome(): Promise<void> {
    await logMeetingOutcome({
      meetingId: meeting!.id, leadId: meeting!.lead_id,
      payload: { status: outcomeStatus, notes: outcomeNotes || undefined },
    });
    resetLocalState();
  }

  return (
    <Drawer open={open} onOpenChange={handleOpenChange}>
      <DrawerContent>
        <DrawerHeader>
          <div className="flex items-center gap-2">
            <DrawerTitle>{meeting.title}</DrawerTitle>
            <MeetingStatusBadge status={meeting.status} />
          </div>
          <DrawerDescription>
            {meeting.lead_full_name}
            {meeting.lead_company_name && ` · ${meeting.lead_company_name}`}
          </DrawerDescription>
        </DrawerHeader>

        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-2 gap-3 text-body-sm">
            <div>
              <dt className="text-caption text-muted-foreground">Owner</dt>
              <dd className="text-foreground">{meeting.owner?.full_name ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">Duration</dt>
              <dd className="text-foreground">{meeting.duration_minutes} min</dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">Scheduled</dt>
              <dd className="text-foreground">
                {meeting.scheduled_start ? format(new Date(meeting.scheduled_start), "PPp") : "Not yet booked"}
              </dd>
            </div>
            {meeting.meeting_url && (
              <div>
                <dt className="text-caption text-muted-foreground">Meet link</dt>
                <dd>
                  <a href={meeting.meeting_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-primary hover:underline">
                    Join <ExternalLink className="size-3" />
                  </a>
                </dd>
              </div>
            )}
          </dl>

          {meeting.description && <p className="text-body-sm text-muted-foreground">{meeting.description}</p>}
          {meeting.notes && (
            <div className="rounded-lg border border-border bg-muted/30 p-3 text-body-sm text-foreground">
              <p className="mb-1 text-caption font-medium text-muted-foreground">Notes</p>
              <p className="whitespace-pre-wrap">{meeting.notes}</p>
            </div>
          )}

          {mode === "reschedule" && (
            <div className="flex flex-col gap-3 rounded-lg border border-border p-4">
              <p className="text-body-sm font-medium text-foreground">Reschedule</p>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="reschedule-start">New start</Label>
                <Input
                  id="reschedule-start" type="datetime-local"
                  defaultValue={meeting.scheduled_start ? toLocalInputValue(meeting.scheduled_start) : undefined}
                  onChange={(event) => setNewStart(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="reschedule-end">New end</Label>
                <Input
                  id="reschedule-end" type="datetime-local"
                  defaultValue={meeting.scheduled_end ? toLocalInputValue(meeting.scheduled_end) : undefined}
                  onChange={(event) => setNewEnd(event.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => setMode("view")}>Cancel</Button>
                <Button size="sm" isLoading={isRescheduling} onClick={() => void handleReschedule()}>Save</Button>
              </div>
            </div>
          )}

          {mode === "outcome" && (
            <div className="flex flex-col gap-3 rounded-lg border border-border p-4">
              <p className="text-body-sm font-medium text-foreground">Log outcome</p>
              <Select value={outcomeStatus} onValueChange={(value) => setOutcomeStatus(value as "completed" | "no_show")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="no_show">No-show</SelectItem>
                </SelectContent>
              </Select>
              <Textarea placeholder="Notes (optional)" rows={3} value={outcomeNotes} onChange={(event) => setOutcomeNotes(event.target.value)} />
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => setMode("view")}>Cancel</Button>
                <Button size="sm" isLoading={isLogging} onClick={() => void handleLogOutcome()}>Save</Button>
              </div>
            </div>
          )}
        </div>

        {mode === "view" && (
          <DrawerFooter>
            {canCancel && (
              <Button variant="danger" onClick={cancelConfirm.open} disabled={isCancelling}>
                <XCircle className="size-4" />
                Cancel meeting
              </Button>
            )}
            {canReschedule && (
              <Button variant="outline" onClick={() => setMode("reschedule")}>
                <CalendarDays className="size-4" />
                Reschedule
              </Button>
            )}
            {canLogOutcome && (
              <Button onClick={() => setMode("outcome")}>
                <CheckCircle2 className="size-4" />
                Log outcome
              </Button>
            )}
          </DrawerFooter>
        )}
      </DrawerContent>

      <ConfirmDialog
        open={cancelConfirm.isOpen}
        onOpenChange={cancelConfirm.onOpenChange}
        title="Cancel this meeting?"
        description="This removes the event from the connected Google Calendar for both you and your lead."
        confirmLabel="Cancel meeting"
        isConfirming={isCancelling}
        onConfirm={() => void handleCancel()}
      >
        <Textarea placeholder="Reason (optional)" rows={2} value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} />
      </ConfirmDialog>
    </Drawer>
  );
}
