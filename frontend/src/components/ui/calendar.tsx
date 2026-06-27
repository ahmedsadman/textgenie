import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker, type DayPickerProps } from "react-day-picker";

import { cn } from "@/lib/utils";

import "react-day-picker/style.css";

type CalendarProps = DayPickerProps & {
  className?: string;
};

function Calendar({ className, classNames, ...props }: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays
      className={cn("p-3 text-sm", className)}
      classNames={{
        months: "flex flex-col gap-3",
        month: "flex flex-col gap-3",
        month_caption: "flex h-7 items-center justify-center font-medium",
        caption_label: "text-sm font-medium",
        nav: "flex items-center justify-between absolute inset-x-3 top-3 pointer-events-none",
        button_previous:
          "size-7 inline-flex items-center justify-center rounded-md border border-transparent hover:bg-muted pointer-events-auto",
        button_next:
          "size-7 inline-flex items-center justify-center rounded-md border border-transparent hover:bg-muted pointer-events-auto",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday:
          "w-8 h-8 text-muted-foreground text-xs font-normal flex items-center justify-center",
        week: "flex w-full",
        day: "w-8 h-8 p-0 text-center",
        day_button:
          "size-8 inline-flex items-center justify-center rounded-md text-sm font-normal hover:bg-muted aria-selected:bg-primary aria-selected:text-primary-foreground aria-selected:hover:bg-primary/80",
        today: "text-primary font-semibold",
        outside: "text-muted-foreground/50",
        disabled: "text-muted-foreground opacity-40 pointer-events-none",
        range_start:
          "[&>button]:bg-primary [&>button]:text-primary-foreground rounded-l-md",
        range_end:
          "[&>button]:bg-primary [&>button]:text-primary-foreground rounded-r-md",
        range_middle: "[&>button]:bg-muted [&>button]:text-foreground",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, ...rest }) =>
          orientation === "left" ? (
            <ChevronLeft className="h-4 w-4" {...rest} />
          ) : (
            <ChevronRight className="h-4 w-4" {...rest} />
          ),
      }}
      {...props}
    />
  );
}

export { Calendar };
