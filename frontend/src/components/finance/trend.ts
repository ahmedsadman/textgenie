import type { TrendDirection } from "@/lib/types";

/** Which movement direction is financially healthy for a given metric. */
export type GoodWhen = "up" | "down";

/**
 * Tailwind text-color class for a trend badge. Colored by *meaning*, not arrow
 * direction: e.g. spending going up is bad (red) while income going up is good
 * (green). Flat / new carry no verdict, so they stay muted.
 */
export function trendColorClass(
  direction: TrendDirection,
  goodWhen: GoodWhen,
): string {
  if (direction === "flat" || direction === "new") {
    return "text-muted-foreground";
  }
  return direction === goodWhen ? "text-emerald-600" : "text-red-600";
}
