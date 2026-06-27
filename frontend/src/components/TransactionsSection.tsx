import { ChevronDown, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import DateRangePicker from "@/components/DateRangePicker";
import PaginationNav from "@/components/PaginationNav";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { api } from "@/lib/api";
import { resolveDateRange, type DateRangeSelection } from "@/lib/dateRange";
import type { Message, PaginatedTransactions } from "@/lib/types";
import { cn, formatMessageDateTime } from "@/lib/utils";

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

type MessageFetchState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "loaded"; message: Message };

export default function TransactionsSection() {
  const [selection, setSelection] = useLocalStorage<DateRangeSelection>(
    STORAGE_KEY,
    DEFAULT_SELECTION,
  );
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedTransactions | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [expandedTxIds, setExpandedTxIds] = useState<Set<number>>(
    () => new Set(),
  );
  const messageCache = useRef<Map<number, Message>>(new Map());
  const inFlight = useRef<Set<number>>(new Set());
  const [messageStates, setMessageStates] = useState<
    Map<number, MessageFetchState>
  >(() => new Map());

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

  const fetchMessage = useCallback((messageId: number) => {
    if (messageCache.current.has(messageId)) return;
    if (inFlight.current.has(messageId)) return;
    inFlight.current.add(messageId);
    setMessageStates((prev) => {
      const next = new Map(prev);
      next.set(messageId, { status: "loading" });
      return next;
    });
    api
      .getMessage(messageId)
      .then((message) => {
        messageCache.current.set(messageId, message);
        setMessageStates((prev) => {
          const next = new Map(prev);
          next.set(messageId, { status: "loaded", message });
          return next;
        });
      })
      .catch(() => {
        setMessageStates((prev) => {
          const next = new Map(prev);
          next.set(messageId, { status: "error" });
          return next;
        });
      })
      .finally(() => {
        inFlight.current.delete(messageId);
      });
  }, []);

  const toggleExpanded = useCallback(
    (txId: number, messageId: number) => {
      const willExpand = !expandedTxIds.has(txId);
      setExpandedTxIds((prev) => {
        const next = new Set(prev);
        if (next.has(txId)) next.delete(txId);
        else next.add(txId);
        return next;
      });
      if (willExpand) fetchMessage(messageId);
    },
    [expandedTxIds, fetchMessage],
  );

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
              const isExpanded = expandedTxIds.has(tx.id);
              const messageState = messageStates.get(tx.message_id);
              return (
                <Collapsible
                  key={tx.id}
                  open={isExpanded}
                  onOpenChange={() => toggleExpanded(tx.id, tx.message_id)}
                >
                  <div
                    role="button"
                    tabIndex={0}
                    aria-expanded={isExpanded}
                    aria-label={`Toggle message for ${tx.sender} ${
                      isIncome ? "+" : "−"
                    }${formatAmount(tx.amount)} on ${formatMessageDateTime(
                      tx.date,
                    )}`}
                    onClick={() => toggleExpanded(tx.id, tx.message_id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleExpanded(tx.id, tx.message_id);
                      }
                    }}
                    className="group flex cursor-pointer items-center justify-between gap-3 p-3 hover:bg-muted/50"
                  >
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 shrink-0 text-muted-foreground transition-all",
                        isExpanded
                          ? "rotate-180 opacity-100"
                          : "opacity-0 group-hover:opacity-100",
                      )}
                    />
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
                  <CollapsibleContent>
                    <div className="border-t bg-muted/30 px-3 py-2.5 pl-10 text-sm text-muted-foreground">
                      {messageState?.status === "loading" && (
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>Loading message…</span>
                        </div>
                      )}
                      {messageState?.status === "error" && (
                        <div className="flex items-center gap-3">
                          <span className="text-destructive">
                            Failed to load message.
                          </span>
                          <button
                            type="button"
                            onClick={() => fetchMessage(tx.message_id)}
                            className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
                          >
                            Retry
                          </button>
                        </div>
                      )}
                      {messageState?.status === "loaded" && (
                        <p className="whitespace-pre-wrap break-words text-foreground">
                          {messageState.message.content}
                        </p>
                      )}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
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
