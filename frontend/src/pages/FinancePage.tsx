import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Pencil, Plus, Trash2, X } from "lucide-react";

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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, type BankUpdate } from "@/lib/api";
import type { Bank } from "@/lib/types";

const MAX_SENDERS = 3;

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

interface EditState {
  name: string;
  balance: string;
  balanceTouched: boolean;
  senders: string[];
  templates: string[];
}

function BankEditPanel({
  bank,
  onSave,
  onCancel,
}: {
  bank: Bank;
  onSave: (bankId: number, update: BankUpdate) => Promise<void>;
  onCancel: () => void;
}) {
  const [state, setState] = useState<EditState>({
    name: bank.name,
    balance: bank.last_balance ?? "",
    balanceTouched: false,
    senders: bank.senders.length > 0 ? bank.senders : [""],
    templates: bank.templates,
  });
  const [saving, setSaving] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const templateRefs = useRef<Map<number, HTMLTextAreaElement>>(new Map());

  useEffect(() => {
    nameInputRef.current?.focus();
  }, []);

  function addSender() {
    if (state.senders.length >= MAX_SENDERS) return;
    setState((s) => ({ ...s, senders: [...s.senders, ""] }));
  }

  function updateSender(index: number, value: string) {
    setState((s) => {
      const senders = [...s.senders];
      senders[index] = value;
      return { ...s, senders };
    });
  }

  function removeSender(index: number) {
    setState((s) => ({
      ...s,
      senders: s.senders.filter((_, i) => i !== index),
    }));
  }

  function addTemplate() {
    setState((s) => ({ ...s, templates: [...s.templates, ""] }));
  }

  function updateTemplate(index: number, value: string) {
    setState((s) => {
      const templates = [...s.templates];
      templates[index] = value;
      return { ...s, templates };
    });
  }

  function removeTemplate(index: number) {
    setState((s) => ({
      ...s,
      templates: s.templates.filter((_, i) => i !== index),
    }));
  }

  function insertVariable(index: number) {
    const textarea = templateRefs.current.get(index);
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const current = state.templates[index];
    const inserted =
      current.substring(0, start) + "{{balance}}" + current.substring(end);
    updateTemplate(index, inserted);
    requestAnimationFrame(() => {
      const pos = start + "{{balance}}".length;
      textarea.focus();
      textarea.setSelectionRange(pos, pos);
    });
  }

  async function handleSave() {
    if (!state.name.trim()) return;
    setSaving(true);
    const update: BankUpdate = {
      name: state.name,
      senders: state.senders.filter((s) => s.trim()),
      templates: state.templates.filter((t) => t.trim()),
    };
    if (state.balanceTouched && state.balance.trim() !== "") {
      update.last_balance = state.balance;
    }
    try {
      await onSave(bank.id, update);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-md border p-4">
      <div>
        <Label htmlFor={`bank-name-${bank.id}`}>Name</Label>
        <Input
          id={`bank-name-${bank.id}`}
          ref={nameInputRef}
          value={state.name}
          onChange={(e) => setState((s) => ({ ...s, name: e.target.value }))}
          placeholder="Bank name"
        />
      </div>

      <div>
        <Label htmlFor={`bank-balance-${bank.id}`}>Balance</Label>
        <Input
          id={`bank-balance-${bank.id}`}
          type="number"
          step="0.01"
          min="0"
          value={state.balance}
          onChange={(e) =>
            setState((s) => ({
              ...s,
              balance: e.target.value,
              balanceTouched: true,
            }))
          }
          placeholder="Balance (optional)"
        />
      </div>

      <div>
        <Label>Sender Names</Label>
        <p className="text-xs text-muted-foreground mb-2">
          How the bank appears as the SMS sender (max {MAX_SENDERS})
        </p>
        <div className="flex flex-col gap-2">
          {state.senders.map((sender, i) => (
            <div key={i} className="flex gap-2">
              <Input
                value={sender}
                onChange={(e) => updateSender(i, e.target.value)}
                placeholder="e.g. BRACBANK"
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeSender(i)}
                aria-label="Remove sender"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          {state.senders.length < MAX_SENDERS && (
            <Button
              variant="outline"
              size="sm"
              onClick={addSender}
              className="w-fit"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add sender
            </Button>
          )}
        </div>
      </div>

      <div>
        <Label>Message Templates</Label>
        <p className="text-xs text-muted-foreground mb-2">
          Paste a real SMS and replace the balance with the variable below
        </p>
        <div className="flex flex-col gap-3">
          {state.templates.map((template, i) => (
            <div key={i} className="flex flex-col gap-1">
              <div className="flex gap-2">
                <textarea
                  ref={(el) => {
                    if (el) templateRefs.current.set(i, el);
                    else templateRefs.current.delete(i);
                  }}
                  value={template}
                  onChange={(e) => updateTemplate(i, e.target.value)}
                  placeholder="e.g. Your A/C balance is TK {{balance}}. For Enquiry call: 16221"
                  rows={3}
                  className="flex-1 rounded-md border bg-transparent px-3 py-2 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeTemplate(i)}
                  aria-label="Remove template"
                  className="self-start"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <button
                  type="button"
                  onClick={() => insertVariable(i)}
                  className="rounded-md bg-muted px-2 py-0.5 text-xs font-mono text-muted-foreground hover:bg-muted/80 cursor-pointer"
                >
                  {"{{balance}}"}
                </button>
              </div>
            </div>
          ))}
          <Button
            variant="outline"
            size="sm"
            onClick={addTemplate}
            className="w-fit"
          >
            <Plus className="h-4 w-4 mr-1" />
            Add template
          </Button>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || !state.name.trim()}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

export default function FinancePage() {
  const [banks, setBanks] = useState<Bank[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  function loadBanks() {
    return api
      .getBanks()
      .then(setBanks)
      .catch(() => toast.error("Failed to load banks"));
  }

  useEffect(() => {
    loadBanks().finally(() => setLoading(false));
  }, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSubmitting(true);

    try {
      await api.createBank({ name: newName });
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

  async function handleSave(bankId: number, update: BankUpdate) {
    try {
      await api.updateBank(bankId, update);
      await loadBanks();
      setEditingId(null);
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
            <ul className="divide-y">
              {banks.map((bank) => (
                <li key={bank.id} className="flex flex-col gap-2 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{bank.name}</p>
                      {bank.last_balance_at && (
                        <p className="text-xs text-muted-foreground">
                          Updated {formatRelativeTime(bank.last_balance_at)}
                        </p>
                      )}
                    </div>
                    <p
                      className={`text-sm tabular-nums ${
                        bank.last_balance === null
                          ? "text-muted-foreground italic"
                          : "font-medium"
                      }`}
                    >
                      {formatBalance(bank.last_balance)}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setEditingId(editingId === bank.id ? null : bank.id)
                      }
                      aria-label="Edit"
                    >
                      {editingId === bank.id ? (
                        <X className="h-4 w-4" />
                      ) : (
                        <Pencil className="h-4 w-4" />
                      )}
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
                            Are you sure you want to delete &quot;{bank.name}
                            &quot;? This action cannot be undone.
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
                  </div>
                  {editingId === bank.id && (
                    <BankEditPanel
                      bank={bank}
                      onSave={handleSave}
                      onCancel={() => setEditingId(null)}
                    />
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
