export type DateRangePresetKey =
  | "last_7_days"
  | "this_month"
  | "last_month"
  | "last_3_months"
  | "last_year"
  | "all_time"
  | "custom";

export interface DateRangeSelection {
  presetKey: DateRangePresetKey;
  customRange: { from: string; to: string } | null;
}

export interface DateRangePreset {
  key: DateRangePresetKey;
  label: string;
}

export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  { key: "last_7_days", label: "Last 7 days" },
  { key: "this_month", label: "This month" },
  { key: "last_month", label: "Last month" },
  { key: "last_3_months", label: "Last 3 months" },
  { key: "last_year", label: "Last year" },
  { key: "all_time", label: "All time" },
];

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0);
}

function endOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}

export function toDateOnlyString(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseDateOnly(s: string): Date {
  const [year, month, day] = s.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function rangeFromDays(now: Date, days: number) {
  const to = endOfDay(now);
  const from = startOfDay(new Date(now.getTime() - days * 24 * 60 * 60 * 1000));
  return { from: from.toISOString(), to: to.toISOString() };
}

export function resolveDateRange(value: DateRangeSelection): {
  from: string | null;
  to: string | null;
} {
  const now = new Date();
  switch (value.presetKey) {
    case "all_time":
      return { from: null, to: null };
    case "last_7_days":
      return rangeFromDays(now, 7);
    case "this_month": {
      const from = startOfDay(new Date(now.getFullYear(), now.getMonth(), 1));
      const to = endOfDay(now);
      return { from: from.toISOString(), to: to.toISOString() };
    }
    case "last_month":
      return rangeFromDays(now, 30);
    case "last_3_months":
      return rangeFromDays(now, 90);
    case "last_year":
      return rangeFromDays(now, 365);
    case "custom": {
      if (!value.customRange) return { from: null, to: null };
      return {
        from: `${value.customRange.from}T00:00:00.000Z`,
        to: `${value.customRange.to}T23:59:59.999Z`,
      };
    }
  }
}

function formatDateShort(d: Date): string {
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function dateRangeLabel(value: DateRangeSelection): string {
  if (value.presetKey === "custom" && value.customRange) {
    const from = parseDateOnly(value.customRange.from);
    const to = parseDateOnly(value.customRange.to);
    return `${formatDateShort(from)} – ${formatDateShort(to)}`;
  }
  return (
    DATE_RANGE_PRESETS.find((p) => p.key === value.presetKey)?.label ??
    "Last month"
  );
}
