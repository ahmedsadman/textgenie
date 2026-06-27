import { useState } from "react";
import { Popover } from "@base-ui/react/popover";
import { CalendarIcon, ChevronDown } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  DATE_RANGE_PRESETS,
  dateRangeLabel,
  parseDateOnly,
  toDateOnlyString,
  type DateRangePresetKey,
  type DateRangeSelection,
} from "@/lib/dateRange";
import { cn } from "@/lib/utils";

interface DateRangePickerProps {
  value: DateRangeSelection;
  onChange: (next: DateRangeSelection) => void;
}

function rangeFromSelection(value: DateRangeSelection): DateRange | undefined {
  if (!value.customRange) return undefined;
  return {
    from: parseDateOnly(value.customRange.from),
    to: parseDateOnly(value.customRange.to),
  };
}

export default function DateRangePicker({
  value,
  onChange,
}: DateRangePickerProps) {
  const [draftRange, setDraftRange] = useState<DateRange | undefined>(
    rangeFromSelection(value),
  );
  const [open, setOpen] = useState(false);
  const [clicksSinceOpen, setClicksSinceOpen] = useState(0);

  const initialPresets = DATE_RANGE_PRESETS.filter((p) => p.key !== "all_time");
  const allTimePreset = DATE_RANGE_PRESETS.find((p) => p.key === "all_time");

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setDraftRange(rangeFromSelection(value));
      setClicksSinceOpen(0);
    }
  }

  function selectPreset(key: DateRangePresetKey) {
    onChange({ presetKey: key, customRange: null });
    setDraftRange(undefined);
    setOpen(false);
  }

  function handleRangeSelect(_range: DateRange | undefined, triggerDate: Date) {
    if (clicksSinceOpen === 0) {
      setDraftRange({ from: triggerDate, to: triggerDate });
      setClicksSinceOpen(1);
      return;
    }

    const from = draftRange?.from;
    if (!from || triggerDate <= from) {
      setDraftRange({ from: triggerDate, to: triggerDate });
      setClicksSinceOpen(1);
      return;
    }

    setDraftRange({ from, to: triggerDate });
    onChange({
      presetKey: "custom",
      customRange: {
        from: toDateOnlyString(from),
        to: toDateOnlyString(triggerDate),
      },
    });
    setOpen(false);
  }

  const defaultMonth = draftRange?.from ?? new Date();

  return (
    <Popover.Root open={open} onOpenChange={handleOpenChange}>
      <Popover.Trigger
        render={
          <Button variant="outline" size="sm" aria-label="Select date range">
            <CalendarIcon className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{dateRangeLabel(value)}</span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        }
      />
      <Popover.Portal>
        <Popover.Positioner sideOffset={4} align="end">
          <Popover.Popup className="z-50 rounded-lg border bg-popover p-3 text-popover-foreground ring-1 ring-foreground/10">
            <div className="flex gap-3">
              <div className="flex w-40 flex-col gap-0.5 border-r pr-3">
                <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">
                  Presets
                </div>
                {initialPresets.map((preset) => (
                  <button
                    key={preset.key}
                    type="button"
                    onClick={() => selectPreset(preset.key)}
                    className={cn(
                      "rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
                      value.presetKey === preset.key && "bg-muted font-medium",
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
                {allTimePreset && (
                  <button
                    type="button"
                    onClick={() => selectPreset(allTimePreset.key)}
                    className={cn(
                      "mt-1 rounded-md border-t px-2 py-1.5 pt-2 text-left text-sm hover:bg-muted",
                      value.presetKey === allTimePreset.key &&
                        "bg-muted font-medium",
                    )}
                  >
                    {allTimePreset.label}
                  </button>
                )}
              </div>
              <Calendar
                mode="range"
                numberOfMonths={2}
                selected={draftRange}
                onSelect={handleRangeSelect}
                defaultMonth={defaultMonth}
                classNames={{ months: "flex flex-row gap-4" }}
              />
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
