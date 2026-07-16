"use client";

import { format } from "date-fns";
import { CalendarDays } from "@/icons";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { Calendar } from "./calendar";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

export interface DatePickerProps {
  value?: Date;
  onChange: (date: Date | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  /** Passed through to the underlying Calendar (e.g. `{ before: new Date() }`). */
  disabledDates?: import("react-day-picker").Matcher | import("react-day-picker").Matcher[];
}

/** A single-date picker: a formatted trigger button that opens a Calendar in a Popover. */
export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  disabled,
  className,
  disabledDates,
}: DatePickerProps): React.ReactElement {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal",
            !value && "text-muted-foreground",
            className,
          )}
        >
          <CalendarDays className="size-4" />
          {value ? format(value, "PPP") : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={onChange}
          disabled={disabledDates}
          autoFocus
        />
      </PopoverContent>
    </Popover>
  );
}
