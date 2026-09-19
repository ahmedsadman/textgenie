import type { ReactNode } from "react";

import Sparkline from "@/components/finance/Sparkline";
import TrendBadge from "@/components/finance/TrendBadge";
import TrendTile from "@/components/finance/TrendTile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrency } from "@/hooks/queries/useCurrency";
import { useTransactionTrends } from "@/hooks/queries/useTransactions";
import { formatAmount } from "@/lib/currency";
import type { Currency, TransactionTrends } from "@/lib/types";

const DASH = "—";

function ratePercent(fraction: string | null): string {
  if (fraction === null) return DASH;
  return `${Math.round(Number(fraction) * 100)}%`;
}

function signedPercent(change: string | null, unit: "%" | "pp"): string {
  if (change === null) return DASH;
  const prefix = Number(change) > 0 ? "+" : "";
  return `${prefix}${change}${unit}`;
}

function AmountTooltip({
  recent,
  prior,
  change,
  currency,
}: {
  recent: string;
  prior: string;
  change: string | null;
  currency: Currency;
}): ReactNode {
  return (
    <div className="flex flex-col gap-0.5">
      <span>Last 3 mo: {formatAmount(recent, currency)}/mo</span>
      <span>Prior 3 mo: {formatAmount(prior, currency)}/mo</span>
      <span>Change: {signedPercent(change, "%")}</span>
    </div>
  );
}

function RateTooltip({ trends }: { trends: TransactionTrends }): ReactNode {
  const { recent, prior, change_pp } = trends.savings_rate;
  return (
    <div className="flex flex-col gap-0.5">
      <span>Last 3 mo: {ratePercent(recent)}</span>
      <span>Prior 3 mo: {ratePercent(prior)}</span>
      <span>Change: {signedPercent(change_pp, "pp")}</span>
    </div>
  );
}

function TrendTiles({
  trends,
  currency,
}: {
  trends: TransactionTrends;
  currency: Currency;
}) {
  const { income, spend, savings_rate } = trends;
  const netPerMonth = Number(income.recent_avg) - Number(spend.recent_avg);

  return (
    <div className="flex flex-wrap gap-x-10 gap-y-6">
      <TrendTile
        label="Income / Month"
        value={formatAmount(income.recent_avg, currency)}
        badge={
          <TrendBadge
            direction={income.direction}
            change={income.change_pct}
            unit="%"
            goodWhen="up"
            tooltip={
              <AmountTooltip
                recent={income.recent_avg}
                prior={income.prior_avg}
                change={income.change_pct}
                currency={currency}
              />
            }
          />
        }
        spark={<Sparkline values={income.spark.map(Number)} />}
      />

      <TrendTile
        label="Spend / Month"
        value={formatAmount(spend.recent_avg, currency)}
        badge={
          <TrendBadge
            direction={spend.direction}
            change={spend.change_pct}
            unit="%"
            goodWhen="down"
            tooltip={
              <AmountTooltip
                recent={spend.recent_avg}
                prior={spend.prior_avg}
                change={spend.change_pct}
                currency={currency}
              />
            }
          />
        }
        spark={<Sparkline values={spend.spark.map(Number)} />}
      />

      <TrendTile
        label="Savings Rate"
        value={ratePercent(savings_rate.recent)}
        subtitle={`${formatAmount(netPerMonth, currency)} net/mo`}
        badge={
          <TrendBadge
            direction={savings_rate.direction}
            change={savings_rate.change_pp}
            unit="pp"
            goodWhen="up"
            tooltip={<RateTooltip trends={trends} />}
          />
        }
        spark={
          <Sparkline
            zeroLine
            values={savings_rate.spark.map((v) =>
              v === null ? null : Number(v) * 100,
            )}
          />
        }
      />
    </div>
  );
}

export default function TrendsSection() {
  const { data: trends, isPending } = useTransactionTrends();
  const { data: currencySettings } = useCurrency();
  const currency: Currency = currencySettings?.currency ?? "BDT";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg sm:text-xl">Trends</CardTitle>
        <p className="text-xs text-muted-foreground">
          Last 3 months · vs previous 3 months
        </p>
      </CardHeader>
      <CardContent>
        {isPending || !trends ? (
          <div className="flex flex-wrap gap-x-10 gap-y-6">
            {["Income / Month", "Spend / Month", "Savings Rate"].map(
              (label) => (
                <TrendTile key={label} label={label} value={DASH} />
              ),
            )}
          </div>
        ) : (
          <TrendTiles trends={trends} currency={currency} />
        )}
      </CardContent>
    </Card>
  );
}
