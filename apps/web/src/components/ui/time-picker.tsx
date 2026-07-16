"use client";

import { Clock3 } from "@/icons";
import { cn } from "@/lib/utils";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";

export interface TimeValue {
  hour: number; // 1-12
  minute: number; // 0-59
  period: "AM" | "PM";
}

export interface TimePickerProps {
  value: TimeValue;
  onChange: (value: TimeValue) => void;
  disabled?: boolean;
  className?: string;
  /** Minute increments offered in the dropdown. Defaults to 5-minute steps. */
  minuteStep?: number;
}

const hours = Array.from({ length: 12 }, (_, i) => i + 1);

/** A three-part hour/minute/period time picker composed from Select — pairs with DatePicker for scheduling flows. */
export function TimePicker({ value, onChange, disabled, className, minuteStep = 5 }: TimePickerProps): React.ReactElement {
  const minutes = Array.from({ length: 60 / minuteStep }, (_, i) => i * minuteStep);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Clock3 className="size-4 shrink-0 text-muted-foreground" />
      <Select
        value={String(value.hour)}
        onValueChange={(hour) => onChange({ ...value, hour: Number(hour) })}
        disabled={disabled}
      >
        <SelectTrigger className="w-16">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {hours.map((hour) => (
            <SelectItem key={hour} value={String(hour)}>
              {String(hour).padStart(2, "0")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <span className="text-muted-foreground">:</span>
      <Select
        value={String(value.minute)}
        onValueChange={(minute) => onChange({ ...value, minute: Number(minute) })}
        disabled={disabled}
      >
        <SelectTrigger className="w-16">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {minutes.map((minute) => (
            <SelectItem key={minute} value={String(minute)}>
              {String(minute).padStart(2, "0")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={value.period}
        onValueChange={(period) => onChange({ ...value, period: period as "AM" | "PM" })}
        disabled={disabled}
      >
        <SelectTrigger className="w-[4.5rem]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="AM">AM</SelectItem>
          <SelectItem value="PM">PM</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
