import { useState } from "react";

import { Pencil, Plus, Trash2 } from "lucide-react";

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
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import BankFormDialog from "@/components/BankFormDialog";
import BillsSection from "@/components/BillsSection";
import TransactionsSection from "@/components/TransactionsSection";
import { useBanks, useDeleteBank } from "@/hooks/queries/useBanks";
import { useCurrency } from "@/hooks/queries/useCurrency";
import { formatAmount } from "@/lib/currency";
import type { Bank, Currency } from "@/lib/types";

function formatBalance(balance: string | null, currency: Currency): string {
  if (balance === null) return "No balance yet";
  return formatAmount(balance, currency);
}

function formatTotal(banks: Bank[], currency: Currency): string {
  const total = banks.reduce(
    (acc, b) => acc + (b.last_balance === null ? 0 : Number(b.last_balance)),
    0,
  );
  return formatAmount(total, currency);
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (seconds < 60) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString();
}

function creditCardLast4(cardDigits: string | null): string | null {
  if (!cardDigits) return null;
  const [, last = ""] = cardDigits.split("|");
  return last || null;
}

export default function FinancePage() {
  const { data: banks, isPending } = useBanks();
  const { data: currencySettings } = useCurrency();
  const deleteBank = useDeleteBank();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBank, setEditingBank] = useState<Bank | null>(null);

  const currency: Currency = currencySettings?.currency ?? "BDT";

  function openAddDialog() {
    setEditingBank(null);
    setDialogOpen(true);
  }

  function openEditDialog(bank: Bank) {
    setEditingBank(bank);
    setDialogOpen(true);
  }

  if (isPending || !banks) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Balance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold tabular-nums">
            {banks.length === 0 ? "—" : formatTotal(banks, currency)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Banks</CardTitle>
          <CardAction>
            <Button onClick={openAddDialog}>
              <Plus className="h-4 w-4" />
              Add Bank
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {banks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No banks yet. Add your first bank to start tracking balances from
              SMS.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {banks.map((bank) => (
                <Card key={bank.id} className="gap-3 py-4">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 truncate">
                      <span className="truncate">{bank.name}</span>
                      {bank.account_type === "credit" && (
                        <Badge variant="muted">Credit</Badge>
                      )}
                    </CardTitle>
                    <CardAction className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEditDialog(bank)}
                        aria-label="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger
                          render={
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Delete"
                            />
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete bank</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete &quot;
                              {bank.name}&quot;? This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              variant="destructive"
                              onClick={() => deleteBank.mutate(bank.id)}
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </CardAction>
                  </CardHeader>
                  <CardContent>
                    {bank.account_type === "credit" ? (
                      <p className="text-sm text-muted-foreground italic">
                        {creditCardLast4(bank.card_digits)
                          ? `Card •••• ${creditCardLast4(bank.card_digits)} · not counted in total`
                          : "Credit card · not counted in total"}
                      </p>
                    ) : (
                      <>
                        <p
                          className={`text-2xl tabular-nums ${
                            bank.last_balance === null
                              ? "text-base text-muted-foreground italic"
                              : "font-semibold"
                          }`}
                        >
                          {formatBalance(bank.last_balance, currency)}
                        </p>
                        {bank.last_balance_at && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            Updated {formatRelativeTime(bank.last_balance_at)}
                          </p>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {dialogOpen && (
        <BankFormDialog
          bank={editingBank}
          onClose={() => setDialogOpen(false)}
        />
      )}

      <BillsSection banks={banks} />

      <TransactionsSection />
    </div>
  );
}
