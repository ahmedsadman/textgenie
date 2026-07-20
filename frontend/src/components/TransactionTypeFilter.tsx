import { Popover } from "@base-ui/react/popover";
import { Check, ChevronDown, Filter } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { TransactionType } from "@/lib/types";
import { cn } from "@/lib/utils";

interface TypeOption {
  value: TransactionType;
  label: string;
  icon: ReactNode;
}

interface TransactionTypeFilterProps {
  value: TransactionType[];
  onChange: (next: TransactionType[]) => void;
  options: TypeOption[];
}

export default function TransactionTypeFilter({
  value,
  onChange,
  options,
}: TransactionTypeFilterProps) {
  const [open, setOpen] = useState(false);

  function toggle(type: TransactionType) {
    const next = value.includes(type)
      ? value.filter((t) => t !== type)
      : [...value, type];
    onChange(next);
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        render={
          <Button variant="outline" size="sm" aria-label="Filter by type">
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{describeSelection(value, options)}</span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        }
      />
      <Popover.Portal>
        <Popover.Positioner sideOffset={4} align="end">
          <Popover.Popup className="z-50 min-w-40 rounded-lg border bg-popover p-1 text-popover-foreground ring-1 ring-foreground/10">
            {options.map((option) => {
              const isSelected = value.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => toggle(option.value)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
                    isSelected && "bg-muted font-medium",
                  )}
                  aria-pressed={isSelected}
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
  );
}

function describeSelection(
  value: TransactionType[],
  options: TypeOption[],
): string {
  if (value.length === 0 || value.length === options.length) return "All types";
  const labels = options
    .filter((o) => value.includes(o.value))
    .map((o) => o.label);
  return labels.join(", ");
}
