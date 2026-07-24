import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChevronDown, ChevronUp, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  useAdminUserUsage,
  useDeleteAdminUser,
} from "@/hooks/queries/useAdmin";
import type { AdminUsageBucket, AdminUsageSummary, User } from "@/lib/types";
import { formatTokens, formatUsdFromMicros } from "@/lib/usage";

interface AdminUserCardProps {
  user: User;
  summary: AdminUsageSummary | undefined;
  summaryLoading: boolean;
  expanded: boolean;
  canDelete: boolean;
  onToggle: () => void;
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatBucketLabel(iso: string, bucket: "day" | "week" | "month") {
  const d = new Date(iso);
  const opts: Intl.DateTimeFormatOptions =
    bucket === "month"
      ? { month: "short", year: "2-digit" }
      : { month: "short", day: "numeric" };
  return d.toLocaleDateString(undefined, opts);
}

export function AdminUserCard({
  user,
  summary,
  summaryLoading,
  expanded,
  canDelete,
  onToggle,
}: AdminUserCardProps) {
  const [from, setFrom] = useState(() => isoDaysAgo(30));
  const [to, setTo] = useState(() => todayIso());
  const [confirmOpen, setConfirmOpen] = useState(false);

  const usageQuery = useAdminUserUsage(user.id, { from, to }, expanded);
  const deleteMutation = useDeleteAdminUser();

  const chartData = useMemo(() => {
    if (!usageQuery.data) return [];
    const bucket = usageQuery.data.bucket;
    return usageQuery.data.series.map((b: AdminUsageBucket) => ({
      label: formatBucketLabel(b.bucket_start, bucket),
      cost: b.cost_micros / 1_000_000,
      tokens: b.tokens,
      costMicros: b.cost_micros,
    }));
  }, [usageQuery.data]);

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync(user.id);
      toast.success(`Deleted ${user.email}`);
      setConfirmOpen(false);
    } catch {
      // toast is handled inside the mutation's onError.
    }
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-base font-semibold">
                {user.name}
              </span>
              {user.is_admin && (
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  Admin
                </span>
              )}
            </div>
            <p className="truncate text-sm text-muted-foreground">
              {user.email}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm md:justify-end">
            <StatBlock label="Lifetime" loading={summaryLoading}>
              {summary
                ? `${formatUsdFromMicros(summary.lifetime_cost_micros)} · ${formatTokens(summary.lifetime_tokens)} tok`
                : "$0.00 · 0 tok"}
            </StatBlock>
            <StatBlock label="Last 30d" loading={summaryLoading}>
              {summary
                ? `${formatUsdFromMicros(summary.last30d_cost_micros)} · ${formatTokens(summary.last30d_tokens)} tok`
                : "$0.00 · 0 tok"}
            </StatBlock>

            <div className="flex items-center gap-1">
              {canDelete && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Delete user"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmOpen(true);
                  }}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                aria-label={expanded ? "Collapse" : "Expand"}
                onClick={onToggle}
              >
                {expanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 space-y-4 border-t pt-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label htmlFor={`from-${user.id}`} className="text-xs">
                    From
                  </Label>
                  <Input
                    id={`from-${user.id}`}
                    type="date"
                    value={from}
                    max={to}
                    onChange={(e) => setFrom(e.target.value)}
                    className="h-8 w-40"
                  />
                </div>
                <div>
                  <Label htmlFor={`to-${user.id}`} className="text-xs">
                    To
                  </Label>
                  <Input
                    id={`to-${user.id}`}
                    type="date"
                    value={to}
                    min={from}
                    onChange={(e) => setTo(e.target.value)}
                    className="h-8 w-40"
                  />
                </div>
              </div>
              <div className="text-sm">
                <p className="text-xs text-muted-foreground">Total messages</p>
                {usageQuery.isLoading ? (
                  <Loader2 className="mt-1 h-4 w-4 animate-spin text-muted-foreground" />
                ) : (
                  <p className="font-medium">
                    {usageQuery.data?.message_count ?? 0}
                  </p>
                )}
              </div>
            </div>

            <div className="h-64 w-full">
              {usageQuery.isLoading ? (
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : chartData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  No usage in selected range.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tickLine={false}
                      axisLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                    />
                    <Tooltip
                      formatter={(_v, _n, item) => {
                        const p = item?.payload as {
                          tokens: number;
                          costMicros: number;
                        };
                        return [
                          `${formatUsdFromMicros(p.costMicros)} · ${formatTokens(p.tokens)} tok`,
                          "Usage",
                        ];
                      }}
                    />
                    <Bar dataKey="cost" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        )}
      </CardContent>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete user</AlertDialogTitle>
            <AlertDialogDescription>
              Delete {user.email}? All their messages, banks, transactions, and
              usage data will be removed. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

function StatBlock({
  label,
  loading,
  children,
}: {
  label: string;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="text-right">
      <p className="text-xs text-muted-foreground">{label}</p>
      {loading ? (
        <Loader2 className="ml-auto mt-1 h-4 w-4 animate-spin text-muted-foreground" />
      ) : (
        <p className="text-sm font-medium">{children}</p>
      )}
    </div>
  );
}
