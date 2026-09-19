import type { ReactNode } from "react";

import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import { trendColorClass, type GoodWhen } from "@/components/finance/trend";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { TrendDirection } from "@/lib/types";
import { cn } from "@/lib/utils";

interface TrendBadgeProps {
  direction: TrendDirection;
  /** Signed change magnitude from the API (e.g. "25.0" / "-5.0"), or null. */
  change: string | null;
  /** Suffix after the number: "%" for amounts, "pp" for the savings rate. */
  unit: "%" | "pp";
  goodWhen: GoodWhen;
  /** Optional richer figures shown on hover/focus. */
  tooltip?: ReactNode;
}

export default function TrendBadge({
  direction,
  change,
  unit,
  goodWhen,
  tooltip,
}: TrendBadgeProps) {
  const color = trendColorClass(direction, goodWhen);

  let content: ReactNode;
  if (direction === "new") {
    content = "New";
  } else if (direction === "flat") {
    content = (
      <>
        <Minus className="h-3 w-3" aria-hidden />
        Steady
      </>
    );
  } else {
    const Arrow = direction === "up" ? ArrowUp : ArrowDown;
    const magnitude =
      change === null ? "" : Math.abs(Number(change)).toFixed(1);
    content = (
      <>
        <Arrow className="h-3 w-3" aria-hidden />
        {magnitude}
        {unit}
      </>
    );
  }

  const badge = (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        color,
      )}
    >
      {content}
    </span>
  );

  if (!tooltip) return badge;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger
          render={
            <button type="button" className="inline-flex cursor-default" />
          }
        >
          {badge}
        </TooltipTrigger>
        <TooltipContent>{tooltip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
