import type { ReactNode } from "react";

interface TrendTileProps {
  /** Title Case metric name, e.g. "Income / Month". */
  label: string;
  /** Formatted headline (already localized) or "—" while loading. */
  value: string;
  badge?: ReactNode;
  spark?: ReactNode;
  subtitle?: ReactNode;
}

export default function TrendTile({
  label,
  value,
  badge,
  spark,
  subtitle,
}: TrendTileProps) {
  return (
    <div className="min-w-36 flex-1">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-1 flex items-center gap-2">
        <span className="text-xl font-semibold tabular-nums sm:text-2xl">
          {value}
        </span>
        {badge}
      </div>
      {subtitle && (
        <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>
      )}
      {spark && <div className="mt-2">{spark}</div>}
    </div>
  );
}
