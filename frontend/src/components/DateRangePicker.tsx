import { useState } from "react";
import { Popover } from "@base-ui/react/popover";
import { CalendarIcon, ChevronDown } from "lucide-react";

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

export default function DateRangePicker({
  value,
  onChange,
}: DateRangePickerProps) {
  const [draftFrom, setDraftFrom] = useState<Date | undefined>(
    value.customRange ? parseDateOnly(value.customRange.from) : undefined,
  );
  const [draftTo, setDraftTo] = useState<Date | undefined>(
    value.customRange ? parseDateOnly(value.customRange.to) : undefined,
  );
  const [customMode, setCustomMode] = useState(value.presetKey === "custom");
  const [open, setOpen] = useState(false);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setCustomMode(value.presetKey === "custom");
      setDraftFrom(
        value.customRange ? parseDateOnly(value.customRange.from) : undefined,
      );
      setDraftTo(
        value.customRange ? parseDateOnly(value.customRange.to) : undefined,
      );
    }
  }

  function selectPreset(key: DateRangePresetKey) {
    onChange({ presetKey: key, customRange: null });
    setOpen(false);
  }

  function applyCustom() {
    if (!draftFrom || !draftTo) return;
    const [from, to] =
      draftFrom <= draftTo ? [draftFrom, draftTo] : [draftTo, draftFrom];
    onChange({
      presetKey: "custom",
      customRange: { from: toDateOnlyString(from), to: toDateOnlyString(to) },
    });
    setOpen(false);
  }

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
          <Popover.Popup className="z-50 rounded-lg border bg-popover p-2 text-popover-foreground ring-1 ring-foreground/10">
            <div className="flex flex-col gap-1">
              {DATE_RANGE_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  onClick={() => selectPreset(preset.key)}
                  className={cn(
                    "rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
                    value.presetKey === preset.key &&
                      !customMode &&
                      "bg-muted font-medium",
                  )}
                >
                  {preset.label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setCustomMode(true)}
                className={cn(
                  "rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
                  customMode && "bg-muted font-medium",
                )}
              >
                Custom range
              </button>
            </div>

            {customMode && (
              <div className="mt-2 border-t pt-2">
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-2">
                  <div>
                    <div className="px-2 pb-1 text-xs text-muted-foreground">
                      From
                    </div>
                    <Calendar
                      mode="single"
                      selected={draftFrom}
                      onSelect={setDraftFrom}
                    />
                  </div>
                  <div>
                    <div className="px-2 pb-1 text-xs text-muted-foreground">
                      To
                    </div>
                    <Calendar
                      mode="single"
                      selected={draftTo}
                      onSelect={setDraftTo}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 px-2 pt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={applyCustom}
                    disabled={!draftFrom || !draftTo}
                  >
                    Apply
                  </Button>
                </div>
              </div>
            )}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
