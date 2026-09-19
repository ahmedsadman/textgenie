import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  YAxis,
} from "recharts";

import { cn } from "@/lib/utils";

interface SparklineProps {
  /** Oldest -> newest. `null` renders a gap (line is not connected across it). */
  values: (number | null)[];
  /** Draw a baseline at 0 and keep it in view (used by the savings rate). */
  zeroLine?: boolean;
  className?: string;
}

/**
 * A minimal trend line: no axes, grid, tooltip or legend — just the shape of
 * the last few months. Neutral color; the badge beside it carries the verdict.
 */
export default function Sparkline({
  values,
  zeroLine = false,
  className,
}: SparklineProps) {
  const data = values.map((v, i) => ({ i, v }));

  return (
    <div className={cn("h-10 w-full text-muted-foreground", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 2, right: 0, bottom: 2, left: 0 }}
        >
          <YAxis
            hide
            domain={
              zeroLine
                ? [
                    (min: number) => Math.min(0, min),
                    (max: number) => Math.max(0, max),
                  ]
                : ["auto", "auto"]
            }
          />
          {zeroLine && (
            <ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.25} />
          )}
          <Line
            type="monotone"
            dataKey="v"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
