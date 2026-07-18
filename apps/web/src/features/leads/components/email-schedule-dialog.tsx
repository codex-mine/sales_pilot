"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TimePicker, type TimeValue } from "@/components/ui/time-picker";

export interface EmailScheduleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isScheduling: boolean;
  onSchedule: (scheduledAt: Date) => Promise<void>;
}

function toDateTime(date: Date, time: TimeValue): Date {
  const hour24 = (time.hour % 12) + (time.period === "PM" ? 12 : 0);
  const result = new Date(date);
  result.setHours(hour24, time.minute, 0, 0);
  return result;
}

export function EmailScheduleDialog({
  open, onOpenChange, isScheduling, onSchedule,
}: EmailScheduleDialogProps): React.ReactElement {
  const [date, setDate] = useState<Date | undefined>(undefined);
  const [time, setTime] = useState<TimeValue>({ hour: 9, minute: 0, period: "AM" });

  async function handleSubmit(): Promise<void> {
    if (!date) return;
    await onSchedule(toDateTime(date, time));
    setDate(undefined);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Schedule this email</DialogTitle>
          <DialogDescription>Choose when this email should send.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <DatePicker value={date} onChange={setDate} disabledDates={{ before: new Date() }} />
          <TimePicker value={time} onChange={setTime} />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void handleSubmit()} isLoading={isScheduling} disabled={!date}>
            Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
