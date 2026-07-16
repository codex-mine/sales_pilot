"use client";

import { DayPicker, type DayPickerProps } from "react-day-picker";
import { ChevronLeft, ChevronRight } from "@/icons";
import { cn } from "@/lib/utils";
import { buttonVariants } from "./button";

export type CalendarProps = DayPickerProps;

/**
 * Date picker grid, built on react-day-picker v9. Every part of the
 * library's default styling is replaced via `classNames` so it renders
 * using only design-system tokens — no library CSS is imported.
 */
export function Calendar({ className, showOutsideDays = true, ...props }: CalendarProps): React.ReactElement {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row gap-4",
        month: "flex flex-col gap-3",
        month_caption: "flex justify-center pt-1 relative items-center",
        caption_label: "text-body-sm font-medium text-foreground",
        nav: "flex items-center gap-1 absolute inset-x-0 justify-between px-1",
        button_previous: cn(
          buttonVariants({ variant: "ghost", size: "icon" }),
          "size-7 p-0 text-muted-foreground hover:text-foreground",
        ),
        button_next: cn(
          buttonVariants({ variant: "ghost", size: "icon" }),
          "size-7 p-0 text-muted-foreground hover:text-foreground",
        ),
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "text-muted-foreground w-9 text-caption font-medium",
        week: "flex w-full mt-1",
        day: "relative p-0 text-center size-9 text-body-sm focus-within:relative focus-within:z-20",
        day_button: cn(
          "size-9 rounded-md p-0 font-normal text-foreground transition-colors",
          "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        ),
        selected: "[&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary-hover",
        today: "[&>button]:font-semibold [&>button]:text-primary",
        outside: "text-muted-foreground opacity-50",
        disabled: "text-muted-foreground opacity-40",
        range_start: "[&>button]:bg-primary [&>button]:text-primary-foreground",
        range_middle: "[&>button]:bg-accent [&>button]:text-accent-foreground [&>button]:rounded-none",
        range_end: "[&>button]:bg-primary [&>button]:text-primary-foreground",
        hidden: "invisible",
        ...props.classNames,
      }}
      components={{
        Chevron: ({ orientation }) =>
          orientation === "left" ? <ChevronLeft className="size-4" /> : <ChevronRight className="size-4" />,
      }}
      {...props}
    />
  );
}
