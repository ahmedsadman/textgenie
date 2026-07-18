import { ChevronDown, Link2Off, Receipt } from "lucide-react";
import { useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { useBills, useUnlinkBillPayments } from "@/hooks/queries/useBills";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { formatAmount } from "@/lib/currency";
import type { Bank, Bill } from "@/lib/types";
import { cn, formatMessageDateTime } from "@/lib/utils";

const PAGE_SIZE = 20;

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function formatStatementPeriod(bill: Bill): string {
  if (bill.statement_period) {
    const [year, month] = bill.statement_period.split("-");
    const idx = Number(month) - 1;
    if (idx >= 0 && idx < 12) return `${MONTH_NAMES[idx]} ${year}`;
  }
  const fallback = new Date(bill.received_at);
  return `${MONTH_NAMES[fallback.getMonth()]} ${fallback.getFullYear()}`;
}

interface CreditCardBillsCardProps {
  bank: Bank;
}

function CreditCardBillsCard({ bank }: CreditCardBillsCardProps) {
  const [expanded, setExpanded] = useState(true);
  const { data, isPending } = useBills({
    page: 1,
    page_size: PAGE_SIZE,
    bank_id: bank.id,
  });
  const unlink = useUnlinkBillPayments();
  const bills = data?.bills ?? [];

  return (
    <Card className="gap-3 py-4">
      <CardHeader
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((v) => !v);
          }
        }}
        className="cursor-pointer select-none"
      >
        <CardTitle className="flex items-center gap-2 truncate">
          <ChevronDown
            className={cn(
              "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
              expanded ? "rotate-0" : "-rotate-90",
            )}
          />
          <Receipt className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate">{bank.name}</span>
          <Badge variant="muted">{bills.length}</Badge>
        </CardTitle>
      </CardHeader>
      <Collapsible open={expanded}>
        <CollapsibleContent>
          <CardContent className="flex flex-col gap-2">
            {isPending ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : bills.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No bills yet for this card.
              </p>
            ) : (
              <ul className="divide-y rounded-md border">
                {bills.map((bill) => (
                  <BillRow
                    key={bill.id}
                    bill={bill}
                    onUnlink={() =>
                      unlink.mutate({
                        billId: bill.id,
                        transactionIds: bill.linked_transaction_ids,
                      })
                    }
                  />
                ))}
              </ul>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

interface BillRowProps {
  bill: Bill;
  onUnlink: () => void;
}

function BillRow({ bill, onUnlink }: BillRowProps) {
  const paid = bill.paid_at !== null;
  const canUnlink = bill.linked_transaction_ids.length > 0;

  return (
    <li className="flex items-center gap-3 p-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {formatStatementPeriod(bill)}
          </span>
          <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 text-xs whitespace-nowrap text-muted-foreground">
            {bill.sender}
          </span>
          <Badge variant={paid ? "muted" : "default"}>
            {paid ? "Paid" : "Due"}
          </Badge>
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          Received {formatMessageDateTime(bill.received_at)}
          {paid && bill.paid_at && (
            <> · Paid {formatMessageDateTime(bill.paid_at)}</>
          )}
        </div>
      </div>
      <div className="whitespace-nowrap text-base font-semibold tabular-nums">
        {formatAmount(bill.normalized_total_due, bill.normalized_currency)}
      </div>
      {canUnlink && (
        <AlertDialog>
          <AlertDialogTrigger
            render={
              <Button variant="ghost" size="icon" aria-label="Unlink payment" />
            }
          >
            <Link2Off className="h-4 w-4" />
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Unlink payment</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove the link between this bill and its payment
                transactions. The transactions themselves will not be deleted.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onUnlink}>Unlink</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </li>
  );
}

interface BillsSectionProps {
  banks: Bank[];
}

export default function BillsSection({ banks }: BillsSectionProps) {
  const [billsCollapsed, setBillsCollapsed] = useLocalStorage(
    "finance.billsCollapsed",
    false,
  );
  const creditCards = banks.filter((b) => b.account_type === "credit");
  if (creditCards.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">
          <button
            type="button"
            aria-expanded={!billsCollapsed}
            onClick={() => setBillsCollapsed((v) => !v)}
            className="-mx-1 flex items-center gap-2 rounded px-1 sm:hidden"
          >
            <ChevronDown
              className={cn(
                "h-5 w-5 shrink-0 text-muted-foreground transition-transform",
                billsCollapsed && "-rotate-90",
              )}
            />
            Credit Card Bills
          </button>
          <span className="hidden sm:inline">Credit Card Bills</span>
        </CardTitle>
      </CardHeader>
      <CardContent
        className={cn(
          "flex flex-col gap-3",
          billsCollapsed && "hidden sm:flex",
        )}
      >
        {creditCards.map((card) => (
          <CreditCardBillsCard key={card.id} bank={card} />
        ))}
      </CardContent>
    </Card>
  );
}
