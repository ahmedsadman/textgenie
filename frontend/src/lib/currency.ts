import type { Currency } from "@/lib/types";

/**
 * Format a monetary value with the currency's ISO code as a trailing suffix
 * (e.g. "1,234.56 BDT" / "100.00 USD"). Consistent regardless of the
 * user's locale-specific currency-symbol placement.
 */
export function formatAmount(
  amount: string | number | null | undefined,
  currency: Currency,
): string {
  return `${formatNumeric(amount)} ${currency}`;
}

/**
 * Format a plain number without a currency label. For contexts where the
 * numeric value may span mixed currencies (e.g. an aggregate total across
 * transactions that were normalized under different preferences) and a
 * currency label would be misleading.
 */
export function formatNumeric(
  amount: string | number | null | undefined,
): string {
  const value = typeof amount === "string" ? Number(amount) : (amount ?? 0);
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(value) ? value : 0);
}
