import { Popover } from "@base-ui/react/popover";
import { Check, ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface SelectOption<TValue extends string> {
  value: TValue;
  label: string;
  icon?: ReactNode;
}

interface SelectProps<TValue extends string> {
  value: TValue;
  onChange: (value: TValue) => void;
  options: SelectOption<TValue>[];
  /** Optional label for screen readers. */
  ariaLabel?: string;
  /** Visually hide the selected option's text — show only its icon. */
  iconOnly?: boolean;
  className?: string;
  disabled?: boolean;
}

export function Select<TValue extends string>({
  value,
  onChange,
  options,
  ariaLabel,
  iconOnly = false,
  className,
  disabled = false,
}: SelectProps<TValue>) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);

  function handleSelect(next: TValue, e: React.MouseEvent) {
    e.stopPropagation();
    onChange(next);
    setOpen(false);
  }

  // The wrapping span swallows pointer/key events so the Select can live
  // inside a clickable row without toggling that row when interacted with.
  // (Putting onClick directly on Popover.Trigger overrides its own click
  // handler and breaks the popover.)
  return (
    <span
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger
          render={
            <Button
              variant="ghost"
              size="sm"
              aria-label={ariaLabel ?? selected?.label}
              disabled={disabled}
              className={cn("gap-1.5", className)}
            />
          }
        >
          {selected?.icon}
          {!iconOnly && <span>{selected?.label}</span>}
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Positioner sideOffset={4} align="end">
            <Popover.Popup className="z-50 min-w-32 rounded-lg border bg-popover p-1 text-popover-foreground ring-1 ring-foreground/10">
              {options.map((option) => {
                const isSelected = option.value === value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={(e) => handleSelect(option.value, e)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
                      isSelected && "bg-muted font-medium",
                    )}
                  >
                    {option.icon}
                    <span className="flex-1">{option.label}</span>
                    {isSelected && <Check className="h-3.5 w-3.5" />}
                  </button>
                );
              })}
            </Popover.Popup>
          </Popover.Positioner>
        </Popover.Portal>
      </Popover.Root>
    </span>
  );
}
