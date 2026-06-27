import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Check, Pencil, Trash2, X } from "lucide-react";

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
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, api, type BankUpdate } from "@/lib/api";
import type { Bank } from "@/lib/types";

function formatBalance(balance: string | null): string {
  if (balance === null) return "No balance yet";
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(balance));
}

function formatTotal(banks: Bank[]): string {
  const total = banks.reduce(
    (acc, b) => acc + (b.last_balance === null ? 0 : Number(b.last_balance)),
    0,
  );
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(total);
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

export default function FinancePage() {
  const [banks, setBanks] = useState<Bank[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingBalance, setEditingBalance] = useState("");
  const [editingBalanceTouched, setEditingBalanceTouched] = useState(false);
  const editInputRef = useRef<HTMLInputElement>(null);

  function loadBanks() {
    return api
      .getBanks()
      .then(setBanks)
      .catch(() => toast.error("Failed to load banks"));
  }

  useEffect(() => {
    loadBanks().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (editingId !== null) {
      editInputRef.current?.focus();
    }
  }, [editingId]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSubmitting(true);

    try {
      await api.createBank(newName);
      await loadBanks();
      setNewName("");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to add bank");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function startEditing(bank: Bank) {
    setEditingId(bank.id);
    setEditingName(bank.name);
    setEditingBalance(bank.last_balance ?? "");
    setEditingBalanceTouched(false);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingName("");
    setEditingBalance("");
    setEditingBalanceTouched(false);
  }

  async function saveEdit(bankId: number) {
    if (!editingName.trim()) return;

    const update: BankUpdate = { name: editingName };
    if (editingBalanceTouched && editingBalance.trim() !== "") {
      update.last_balance = editingBalance;
    }

    try {
      await api.updateBank(bankId, update);
      await loadBanks();
      cancelEditing();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to update bank");
      }
    }
  }

  async function handleDelete(bankId: number) {
    try {
      await api.deleteBank(bankId);
      await loadBanks();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to delete bank");
      }
    }
  }

  if (loading || !banks) {
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
            {banks.length === 0 ? "—" : formatTotal(banks)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Banks</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <form onSubmit={handleAdd} className="flex gap-2">
            <Input
              placeholder="New bank name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <Button type="submit" disabled={submitting || !newName.trim()}>
              {submitting ? "Adding..." : "Add"}
            </Button>
          </form>

          {banks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No banks yet. Add your first bank to start tracking balances from
              SMS.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {banks.map((bank) => (
                <Card key={bank.id} className="gap-3 py-4">
                  {editingId === bank.id ? (
                    <CardContent className="flex flex-col gap-2">
                      <Input
                        ref={editInputRef}
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        placeholder="Bank name"
                      />
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editingBalance}
                        onChange={(e) => {
                          setEditingBalance(e.target.value);
                          setEditingBalanceTouched(true);
                        }}
                        placeholder="Balance (optional)"
                      />
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => saveEdit(bank.id)}
                          aria-label="Save"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={cancelEditing}
                          aria-label="Cancel"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  ) : (
                    <>
                      <CardHeader>
                        <CardTitle className="truncate">{bank.name}</CardTitle>
                        <CardAction className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => startEditing(bank)}
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
                                  {bank.name}&quot;? This action cannot be
                                  undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  variant="destructive"
                                  onClick={() => handleDelete(bank.id)}
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </CardAction>
                      </CardHeader>
                      <CardContent>
                        <p
                          className={`text-2xl tabular-nums ${
                            bank.last_balance === null
                              ? "text-base text-muted-foreground italic"
                              : "font-semibold"
                          }`}
                        >
                          {formatBalance(bank.last_balance)}
                        </p>
                        {bank.last_balance_at && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            Updated {formatRelativeTime(bank.last_balance_at)}
                          </p>
                        )}
                      </CardContent>
                    </>
                  )}
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
