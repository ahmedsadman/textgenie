import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Check, Copy, Loader2, RefreshCw } from "lucide-react";

import CategoriesSection from "@/components/CategoriesSection";
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
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ChipInput } from "@/components/ui/chip-input";
import { Input } from "@/components/ui/input";
import { Select, type SelectOption } from "@/components/ui/select";
import { useCurrency, useUpdateCurrency } from "@/hooks/queries/useCurrency";
import { ApiError, api } from "@/lib/api";
import {
  CURRENCY_OPTIONS,
  type Currency,
  type WebhookSettings,
} from "@/lib/types";

const CURRENCY_LABELS: Record<Currency, string> = {
  BDT: "BDT — Bangladeshi Taka",
  USD: "USD — US Dollar",
  EUR: "EUR — Euro",
};

const CURRENCY_SELECT_OPTIONS: SelectOption<Currency>[] = CURRENCY_OPTIONS.map(
  (c) => ({ value: c, label: CURRENCY_LABELS[c] }),
);

export default function SettingsPage() {
  const [webhook, setWebhook] = useState<WebhookSettings | null>(null);
  const [copied, setCopied] = useState(false);
  const [regenerateOpen, setRegenerateOpen] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const [blacklist, setBlacklist] = useState<string[]>([]);
  const [initialBlacklist, setInitialBlacklist] = useState<string[]>([]);
  const [senderSuggestions, setSenderSuggestions] = useState<string[]>([]);
  const [savingBlacklist, setSavingBlacklist] = useState(false);

  const [loading, setLoading] = useState(true);

  const { data: currencyData, isPending: currencyPending } = useCurrency();
  const updateCurrency = useUpdateCurrency();
  const [pendingCurrency, setPendingCurrency] = useState<Currency | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [webhookData, blacklistData, sendersData] = await Promise.all([
          api.getWebhookSettings(),
          api.getMetadataBlacklist(),
          api.getMessageSenders(),
        ]);
        if (cancelled) return;
        setWebhook(webhookData);
        setBlacklist(blacklistData.senders);
        setInitialBlacklist(blacklistData.senders);
        setSenderSuggestions(sendersData);
      } catch {
        if (!cancelled) toast.error("Failed to load settings");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCopy() {
    if (!webhook) return;
    await navigator.clipboard.writeText(webhook.webhook_url);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      const data = await api.regenerateWebhookToken();
      setWebhook(data);
      toast.success("Webhook token regenerated");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to regenerate token");
      }
    } finally {
      setRegenerating(false);
      setRegenerateOpen(false);
    }
  }

  async function handleSaveBlacklist() {
    setSavingBlacklist(true);
    try {
      const data = await api.updateMetadataBlacklist(blacklist);
      setBlacklist(data.senders);
      setInitialBlacklist(data.senders);
      toast.success("Blacklist saved");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to save blacklist");
      }
    } finally {
      setSavingBlacklist(false);
    }
  }

  const savedCurrency: Currency = currencyData?.currency ?? "BDT";
  const selectedCurrency: Currency = pendingCurrency ?? savedCurrency;
  const currencyDirty =
    pendingCurrency !== null && pendingCurrency !== savedCurrency;

  function handleSaveCurrency() {
    if (!currencyDirty || pendingCurrency === null) return;
    updateCurrency.mutate(pendingCurrency, {
      onSuccess: (data) => {
        setPendingCurrency(null);
        toast.success(`Currency saved as ${data.currency}`);
      },
    });
  }

  const blacklistDirty =
    blacklist.length !== initialBlacklist.length ||
    blacklist.some((s, i) => s !== initialBlacklist[i]);

  if (loading) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-2xl">Settings</CardTitle>
          <CardDescription>
            Configure your webhook and message-processing preferences.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Webhook</CardTitle>
          <CardDescription>
            POST SMS messages to this URL to ingest them. Keep this token
            secret.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <label className="text-sm font-medium">Webhook URL</label>
          <div className="flex gap-2">
            <Input
              readOnly
              value={webhook?.webhook_url ?? ""}
              className="flex-1 font-mono text-xs"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopy}
              aria-label="Copy webhook URL"
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
            <AlertDialog
              open={regenerateOpen}
              onOpenChange={(open) => {
                if (!regenerating) setRegenerateOpen(open);
              }}
            >
              <AlertDialogTrigger
                render={
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="Regenerate token"
                  />
                }
              >
                <RefreshCw className="h-4 w-4" />
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Regenerate token</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will invalidate your current webhook URL. Any devices
                    using the old URL will stop working.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={regenerating}>
                    Cancel
                  </AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={handleRegenerate}
                    disabled={regenerating}
                  >
                    {regenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      "Regenerate"
                    )}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </CardContent>
      </Card>

      <CategoriesSection />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Currency</CardTitle>
          <CardDescription>
            The currency all transactions are normalized to. Changes only affect
            future records — existing transactions keep their original currency.
            Bank balances are cleared when the currency changes and refresh from
            the next matching-currency SMS.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-3">
          {currencyPending ? (
            <span className="text-sm text-muted-foreground">Loading...</span>
          ) : (
            <Select<Currency>
              value={selectedCurrency}
              onChange={setPendingCurrency}
              options={CURRENCY_SELECT_OPTIONS}
              ariaLabel="Normalized currency"
              disabled={updateCurrency.isPending}
            />
          )}
          <Button
            onClick={handleSaveCurrency}
            disabled={!currencyDirty || updateCurrency.isPending}
            aria-label="Save currency"
          >
            {updateCurrency.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save"
            )}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Metadata blacklist</CardTitle>
          <CardDescription>
            Messages from these senders will still be categorized, but will not
            be sent for bank-balance extraction. Useful for senders like telco
            operators whose messages can look like transactions but are not.
            Matching is case-insensitive.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <ChipInput
            value={blacklist}
            onChange={setBlacklist}
            suggestions={senderSuggestions}
            placeholder="Type a sender and press Enter, or pick from recent senders"
            ariaLabel="Blacklisted senders"
            disabled={savingBlacklist}
          />
          <div className="flex justify-end">
            <Button
              onClick={handleSaveBlacklist}
              disabled={savingBlacklist || !blacklistDirty}
              aria-label="Save blacklist"
            >
              {savingBlacklist ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save"
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
