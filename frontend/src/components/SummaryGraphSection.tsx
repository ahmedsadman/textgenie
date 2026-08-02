import { useId, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";

import DateRangePicker from "@/components/DateRangePicker";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useCurrency } from "@/hooks/queries/useCurrency";
import { useTransactionSummary } from "@/hooks/queries/useTransactions";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { formatAmount, formatCompact } from "@/lib/currency";
import { resolveDateRange, type DateRangeSelection } from "@/lib/dateRange";

const STORAGE_KEY = "finance.summaryRange";
const DEFAULT_SELECTION: DateRangeSelection = {
  presetKey: "last_year",
  customRange: null,
};

const INCOME_COLOR = "#10b981"; // emerald-500
const EXPENSE_COLOR = "#ef4444"; // red-500

export default function SummaryGraphSection() {
  const [selection, setSelection] = useLocalStorage<DateRangeSelection>(
    STORAGE_KEY,
    DEFAULT_SELECTION,
  );

  const resolved = useMemo(() => resolveDateRange(selection), [selection]);
  const queryParams = useMemo(
    () => ({
      from_date: resolved.from ?? undefined,
      to_date: resolved.to ?? undefined,
    }),
    [resolved.from, resolved.to],
  );

  const { data, isPending } = useTransactionSummary(queryParams);
  const { data: currencySettings } = useCurrency();
  const currency = currencySettings?.currency ?? "BDT";

  // Unique gradient ids so multiple chart instances can't clash in the SVG namespace.
  const gradientId = useId();
  const incomeFill = `income-${gradientId}`;
  const expenseFill = `expense-${gradientId}`;

  const chartData = useMemo(
    () =>
      (data?.series ?? []).map((b) => ({
        label: new Date(b.month_start).toLocaleDateString(undefined, {
          month: "short",
          year: "2-digit",
        }),
        income: Number(b.income),
        expense: Number(b.expense),
      })),
    [data],
  );

  return (
    <Card className="rounded-none bg-transparent py-0 ring-0 sm:rounded-xl sm:bg-card sm:py-4 sm:ring-1">
      <CardHeader className="px-0 sm:px-4">
        <CardTitle className="text-lg sm:text-2xl">Summary Graph</CardTitle>
        <CardAction>
          <DateRangePicker value={selection} onChange={setSelection} />
        </CardAction>
      </CardHeader>
      <CardContent className="px-0 sm:px-4">
        <div className="h-72 w-full">
          {isPending ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No transactions in selected range.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id={incomeFill} x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0"
                      stopColor={INCOME_COLOR}
                      stopOpacity={0.4}
                    />
                    <stop offset="1" stopColor={INCOME_COLOR} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id={expenseFill} x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0"
                      stopColor={EXPENSE_COLOR}
                      stopOpacity={0.4}
                    />
                    <stop
                      offset="1"
                      stopColor={EXPENSE_COLOR}
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={formatCompact}
                  width={64}
                />
                <Tooltip
                  formatter={(value, name) => [
                    formatAmount(value as number, currency),
                    name === "income" ? "Income" : "Expense",
                  ]}
                />
                <Legend
                  formatter={(value) =>
                    value === "income" ? "Income" : "Expense"
                  }
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  stroke={INCOME_COLOR}
                  strokeWidth={2}
                  fill={`url(#${incomeFill})`}
                  dot
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  stroke={EXPENSE_COLOR}
                  strokeWidth={2}
                  fill={`url(#${expenseFill})`}
                  dot
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
