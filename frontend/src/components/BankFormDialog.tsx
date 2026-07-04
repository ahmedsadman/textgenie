import { Info } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useCreateBank, useUpdateBank } from "@/hooks/queries/useBanks";
import type { BankCreate, BankUpdate } from "@/lib/api";
import type { Bank } from "@/lib/types";

const FOUR_DIGITS = /^\d{4}$/;
const CREDIT_TOOLTIP =
  "Credit cards report a limit, not real money. Marking this excludes the account from your total balance and lets us match its SMS by card digits.";

function splitCardDigits(card: string | null | undefined): [string, string] {
  if (!card) return ["", ""];
  const [first = "", last = ""] = card.split("|");
  return [first, last];
}

function onlyDigits(value: string): string {
  return value.replace(/\D/g, "").slice(0, 4);
}

interface BankFormDialogProps {
  bank: Bank | null;
  onClose: () => void;
}

export default function BankFormDialog({ bank, onClose }: BankFormDialogProps) {
  // The parent mounts this component only while the dialog is open, so
  // useState initializers seed once per open — no reset effect needed.
  const isEdit = bank !== null;
  const [initialFirst, initialLast] = splitCardDigits(bank?.card_digits);

  const [name, setName] = useState(bank?.name ?? "");
  const [isCredit, setIsCredit] = useState(bank?.account_type === "credit");
  const [cardFirst4, setCardFirst4] = useState(initialFirst);
  const [cardLast4, setCardLast4] = useState(initialLast);
  const [balance, setBalance] = useState(bank?.last_balance ?? "");
  const [balanceTouched, setBalanceTouched] = useState(false);

  const createBank = useCreateBank();
  const updateBank = useUpdateBank();
  const submitting = createBank.isPending || updateBank.isPending;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    if (
      isCredit &&
      (!FOUR_DIGITS.test(cardFirst4) || !FOUR_DIGITS.test(cardLast4))
    ) {
      toast.error("Enter the first 4 and last 4 digits of the card");
      return;
    }

    if (isEdit && bank) {
      const update: BankUpdate = {
        name,
        account_type: isCredit ? "credit" : "deposit",
      };
      if (isCredit) {
        update.card_digits = `${cardFirst4}|${cardLast4}`;
      } else if (balanceTouched && balance.trim() !== "") {
        update.last_balance = balance;
      }
      updateBank.mutate({ id: bank.id, data: update }, { onSuccess: onClose });
    } else {
      const create: BankCreate = isCredit
        ? {
            name,
            account_type: "credit",
            card_digits: `${cardFirst4}|${cardLast4}`,
          }
        : { name };
      createBank.mutate(create, { onSuccess: onClose });
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{isEdit ? "Edit bank" : "Add bank"}</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="bank-name">Name</Label>
              <Input
                id="bank-name"
                placeholder="Bank name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>

            <Label className="flex items-center gap-2 text-sm font-normal">
              <input
                type="checkbox"
                checked={isCredit}
                onChange={(e) => setIsCredit(e.target.checked)}
              />
              Credit card account
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger
                    render={
                      <button
                        type="button"
                        aria-label="What is a credit card account?"
                        className="inline-flex text-muted-foreground hover:text-foreground"
                      />
                    }
                  >
                    <Info className="h-4 w-4" />
                  </TooltipTrigger>
                  <TooltipContent>{CREDIT_TOOLTIP}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </Label>

            {isCredit ? (
              <div className="flex flex-col gap-1.5">
                <Label>Card digits</Label>
                <div className="flex gap-2">
                  <Input
                    aria-label="Card first 4 digits"
                    placeholder="First 4"
                    inputMode="numeric"
                    maxLength={4}
                    value={cardFirst4}
                    onChange={(e) => setCardFirst4(onlyDigits(e.target.value))}
                  />
                  <Input
                    aria-label="Card last 4 digits"
                    placeholder="Last 4"
                    inputMode="numeric"
                    maxLength={4}
                    value={cardLast4}
                    onChange={(e) => setCardLast4(onlyDigits(e.target.value))}
                  />
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="bank-balance">Balance</Label>
                <Input
                  id="bank-balance"
                  type="number"
                  step="0.01"
                  min="0"
                  value={balance}
                  onChange={(e) => {
                    setBalance(e.target.value);
                    setBalanceTouched(true);
                  }}
                  placeholder="Balance (optional)"
                />
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !name.trim()}>
              {submitting ? "Saving..." : isEdit ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
