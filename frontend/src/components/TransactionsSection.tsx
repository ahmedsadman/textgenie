import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import DateRangePicker from "@/components/DateRangePicker";
import PaginationNav from "@/components/PaginationNav";
import { resolveDateRange, type DateRangeSelection } from "@/lib/dateRange";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { api } from "@/lib/api";
import type { PaginatedTransactions } from "@/lib/types";
import { formatMessageDateTime } from "@/lib/utils";

const PAGE_SIZE = 10;
const STORAGE_KEY = "finance.txRange";
const DEFAULT_SELECTION: DateRangeSelection = {
  presetKey: "last_month",
  customRange: null,
};

function formatAmount(raw: string): string {
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(raw));
}

export default function TransactionsSection() {
  const [selection, setSelection] = useLocalStorage<DateRangeSelection>(
    STORAGE_KEY,
    DEFAULT_SELECTION,
  );
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedTransactions | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);

  const resolved = useMemo(() => resolveDateRange(selection), [selection]);

  useEffect(() => {
    let cancelled = false;

    api
      .getTransactions({
        page,
        page_size: PAGE_SIZE,
        from_date: resolved.from ?? undefined,
        to_date: resolved.to ?? undefined,
      })
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch(() => {
        if (!cancelled) toast.error("Failed to load transactions");
      })
      .finally(() => {
        if (!cancelled) setHasLoaded(true);
      });

    return () => {
      cancelled = true;
    };
  }, [page, resolved.from, resolved.to]);

  function handleSelectionChange(next: DateRangeSelection) {
    setSelection(next);
    setPage(1);
  }

  const totals = data?.totals ?? { income: "0", expense: "0" };
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Transactions</CardTitle>
        <CardAction>
          <DateRangePicker value={selection} onChange={handleSelectionChange} />
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border p-3">
            <div className="text-xs font-medium text-muted-foreground">
              Income
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
              {formatAmount(totals.income)}
            </div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs font-medium text-muted-foreground">
              Expense
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-red-600 dark:text-red-400">
              {formatAmount(totals.expense)}
            </div>
          </div>
        </div>

        {!hasLoaded ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Loading...
          </p>
        ) : !data || data.transactions.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No transactions in this range.
          </p>
        ) : (
          <div className="flex flex-col divide-y rounded-lg border">
            {data.transactions.map((tx) => {
              const isIncome = tx.type === "income";
              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between gap-3 p-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {tx.sender}
                      </span>
                      {tx.bank_name && (
                        <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                          {tx.bank_name}
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {formatMessageDateTime(tx.date)}
                    </div>
                  </div>
                  <div
                    className={`whitespace-nowrap text-base font-semibold tabular-nums ${
                      isIncome
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {isIncome ? "+" : "−"}
                    {formatAmount(tx.amount)}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <PaginationNav
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </CardContent>
    </Card>
  );
}
