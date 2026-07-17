import {
  ArrowDownRight,
  ArrowLeftRight,
  ArrowUpLeft,
  ChevronDown,
  Link2,
  Loader2,
  Receipt,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";

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
import { Select, type SelectOption } from "@/components/ui/select";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import {
  useTransactions,
  useUpdateTransactionType,
} from "@/hooks/queries/useTransactions";
import { api } from "@/lib/api";
import { formatAmount, formatNumeric } from "@/lib/currency";
import { resolveDateRange, type DateRangeSelection } from "@/lib/dateRange";
import type { Message, Transaction, TransactionType } from "@/lib/types";
import { cn, formatMessageDateTime } from "@/lib/utils";

const PAGE_SIZE = 10;
const STORAGE_KEY = "finance.txRange";
const DEFAULT_SELECTION: DateRangeSelection = {
  presetKey: "last_month",
  customRange: null,
};

const TYPE_OPTIONS: SelectOption<TransactionType>[] = [
  {
    value: "expense",
    label: "Expense",
    icon: (
      <ArrowDownRight className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
    ),
  },
  {
    value: "income",
    label: "Income",
    icon: (
      <ArrowUpLeft className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
    ),
  },
  {
    value: "transfer",
    label: "Transfer",
    icon: <ArrowLeftRight className="h-3.5 w-3.5 text-muted-foreground" />,
  },
];

function amountSign(type: TransactionType): string {
  if (type === "income") return "+";
  if (type === "expense") return "−";
  return "";
}

function amountColorClass(type: TransactionType): string {
  if (type === "income") return "text-emerald-600 dark:text-emerald-400";
  if (type === "expense") return "text-red-600 dark:text-red-400";
  return "text-muted-foreground";
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
  const [expandedTxIds, setExpandedTxIds] = useState<Set<number>>(
    () => new Set(),
  );
  const messageCache = useRef<Map<number, Message>>(new Map());
  const inFlight = useRef<Set<number>>(new Set());
  const [messageStates, setMessageStates] = useState<
    Map<number, MessageFetchState>
  >(() => new Map());

  const resolved = useMemo(() => resolveDateRange(selection), [selection]);
  const queryParams = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      from_date: resolved.from ?? undefined,
      to_date: resolved.to ?? undefined,
    }),
    [page, resolved.from, resolved.to],
  );

  const { data, isPending } = useTransactions(queryParams);
  const updateType = useUpdateTransactionType(queryParams);

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
    (tx: Transaction) => {
      const willExpand = !expandedTxIds.has(tx.id);
      setExpandedTxIds((prev) => {
        const next = new Set(prev);
        if (next.has(tx.id)) next.delete(tx.id);
        else next.add(tx.id);
        return next;
      });
      if (willExpand) {
        fetchMessage(tx.message_id);
        if (tx.paired_with_message_id !== null) {
          fetchMessage(tx.paired_with_message_id);
        }
      }
    },
    [expandedTxIds, fetchMessage],
  );

  const handleTypeChange = useCallback(
    (tx: Transaction, newType: TransactionType) => {
      if (newType === tx.type) return;
      updateType.mutate({ id: tx.id, type: newType });
    },
    [updateType],
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
            <div className="mt-1 text-xl font-semibold tabular-nums text-emerald-600 sm:text-2xl dark:text-emerald-400">
              {formatNumeric(totals.income)}
            </div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs font-medium text-muted-foreground">
              Expense
            </div>
            <div className="mt-1 text-xl font-semibold tabular-nums text-red-600 sm:text-2xl dark:text-red-400">
              {formatNumeric(totals.expense)}
            </div>
          </div>
        </div>

        {isPending ? (
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
              const isExpanded = expandedTxIds.has(tx.id);
              const ownMessageState = messageStates.get(tx.message_id);
              const pairedMessageState =
                tx.paired_with_message_id !== null
                  ? messageStates.get(tx.paired_with_message_id)
                  : undefined;
              const isPaired = tx.paired_with_id !== null;
              const sign = amountSign(tx.type);
              return (
                <Collapsible
                  key={tx.id}
                  open={isExpanded}
                  onOpenChange={() => toggleExpanded(tx)}
                >
                  <div
                    role="button"
                    tabIndex={0}
                    aria-expanded={isExpanded}
                    aria-label={`Toggle message for ${tx.sender} ${sign}${formatAmount(
                      tx.normalized_amount,
                      tx.normalized_currency,
                    )} on ${formatMessageDateTime(tx.date)}`}
                    onClick={() => toggleExpanded(tx)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleExpanded(tx);
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
                          <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 text-xs whitespace-nowrap text-muted-foreground">
                            {tx.bank_name}
                          </span>
                        )}
                        {tx.bank_account_type === "credit" && (
                          <span
                            className="shrink-0 rounded-md bg-amber-100 px-1.5 py-0.5 text-xs whitespace-nowrap text-amber-800 dark:bg-amber-950 dark:text-amber-200"
                            title="Credit card — excluded from bank balance"
                          >
                            Credit
                          </span>
                        )}
                        {isPaired && (
                          <Link2
                            className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                            aria-label="Linked transfer — paired with another transaction"
                          />
                        )}
                        {tx.bill_id !== null && (
                          <Receipt
                            className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                            aria-label="Linked to a credit card bill"
                          />
                        )}
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {formatMessageDateTime(tx.date)}
                      </div>
                    </div>
                    <div
                      className={cn(
                        "whitespace-nowrap text-base font-semibold tabular-nums",
                        amountColorClass(tx.type),
                      )}
                    >
                      {sign}
                      {formatAmount(
                        tx.normalized_amount,
                        tx.normalized_currency,
                      )}
                    </div>
                    <Select<TransactionType>
                      value={tx.type}
                      onChange={(t) => handleTypeChange(tx, t)}
                      options={TYPE_OPTIONS}
                      ariaLabel={`Change transaction type (currently ${tx.type})`}
                      iconOnly
                    />
                  </div>
                  <CollapsibleContent>
                    <div className="flex flex-col gap-2 border-t bg-muted/30 px-3 py-2.5 pl-10 text-sm text-muted-foreground">
                      <MessageBlock
                        sender={tx.sender}
                        state={ownMessageState}
                        onRetry={() => fetchMessage(tx.message_id)}
                      />
                      {isPaired && tx.paired_with_message_id !== null && (
                        <MessageBlock
                          sender={pairedSenderLabel(pairedMessageState)}
                          state={pairedMessageState}
                          onRetry={() =>
                            tx.paired_with_message_id !== null &&
                            fetchMessage(tx.paired_with_message_id)
                          }
                          paired
                        />
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

function pairedSenderLabel(state: MessageFetchState | undefined): string {
  if (state?.status === "loaded") return state.message.sender;
  return "Paired transaction";
}

interface MessageBlockProps {
  sender: string;
  state: MessageFetchState | undefined;
  onRetry: () => void;
  paired?: boolean;
}

function MessageBlock({
  sender,
  state,
  onRetry,
  paired = false,
}: MessageBlockProps) {
  return (
    <div className={cn(paired && "border-t border-dashed pt-2")}>
      <div className="mb-0.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        {paired && <Link2 className="h-3 w-3" />}
        <span>{sender}</span>
      </div>
      {state?.status === "loading" && (
        <div className="flex items-center gap-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Loading message…</span>
        </div>
      )}
      {state?.status === "error" && (
        <div className="flex items-center gap-3">
          <span className="text-destructive">Failed to load message.</span>
          <button
            type="button"
            onClick={onRetry}
            className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
          >
            Retry
          </button>
        </div>
      )}
      {state?.status === "loaded" && (
        <p className="whitespace-pre-wrap break-words text-foreground">
          {state.message.content}
        </p>
      )}
    </div>
  );
}
