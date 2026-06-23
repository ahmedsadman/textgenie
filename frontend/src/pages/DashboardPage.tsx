import { useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { toast } from "sonner";
import { Popover } from "@base-ui/react/popover";

import {
  ChevronDown,
  ChevronRight,
  Check,
  Copy,
  Filter,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";

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
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import type {
  Category,
  PaginatedMessages,
  User,
  WebhookSettings,
} from "@/lib/types";
import { cn, getCategoryColor } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function DashboardPage() {
  const { user } = useOutletContext<{ user: User }>();

  const [webhook, setWebhook] = useState<WebhookSettings | null>(null);
  const [instructionsOpen, setInstructionsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const [categories, setCategories] = useState<Category[]>([]);
  const [messages, setMessages] = useState<PaginatedMessages | null>(null);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const trimmedSearch = debouncedSearch.trim();
      try {
        const [webhookData, categoriesData, messagesData] = await Promise.all([
          webhook ? Promise.resolve(webhook) : api.getWebhookSettings(),
          categories.length > 0
            ? Promise.resolve(categories)
            : api.getCategories(),
          api.getMessages({
            page,
            page_size: PAGE_SIZE,
            category_ids:
              selectedCategories.length > 0 ? selectedCategories : undefined,
            search: trimmedSearch || undefined,
          }),
        ]);
        if (cancelled) return;
        setWebhook(webhookData);
        setCategories(categoriesData);
        setMessages(messagesData);
      } catch {
        if (!cancelled) toast.error("Failed to load messages");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [page, selectedCategories, debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
  }

  function toggleCategory(id: number) {
    setSelectedCategories((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
    setPage(1);
  }

  function clearCategoryFilter() {
    setSelectedCategories([]);
    setPage(1);
  }

  async function handleCopy() {
    if (!webhook) return;
    await navigator.clipboard.writeText(webhook.webhook_url);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleRegenerate() {
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
    }
  }

  async function handleDeleteMessage(messageId: number) {
    try {
      await api.deleteMessage(messageId);
      if (messages) {
        const remaining = messages.messages.filter((m) => m.id !== messageId);
        if (remaining.length === 0 && page > 1) {
          setPage(page - 1);
        } else {
          setMessages({
            ...messages,
            messages: remaining,
            total: messages.total - 1,
          });
        }
      }
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to delete message");
      }
    }
  }

  if (loading) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  const totalPages = messages ? Math.ceil(messages.total / PAGE_SIZE) : 0;
  const hasFilter =
    debouncedSearch.trim() !== "" || selectedCategories.length > 0;

  function filterTriggerLabel() {
    if (selectedCategories.length === 0) return "All";
    const names = selectedCategories.map((id) => {
      if (id === 0) return "Uncategorized";
      const cat = categories.find((c) => c.id === id);
      return cat?.name ?? "";
    });
    if (names.length <= 2) return names.join(", ");
    return `${names.length} selected`;
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Dashboard</CardTitle>
          <CardDescription>Welcome back, {user.name}!</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
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
              <AlertDialog>
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
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      variant="destructive"
                      onClick={handleRegenerate}
                    >
                      Regenerate
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>

          <div>
            <button
              onClick={() => setInstructionsOpen(!instructionsOpen)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {instructionsOpen ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              Setup Instructions
            </button>
            {instructionsOpen && (
              <pre className="mt-2 rounded-lg bg-muted p-3 text-xs overflow-x-auto">
                {`POST ${webhook?.webhook_url ?? "<webhook-url>"}
Content-Type: application/json

{
  "sender": "+1234567890",
  "content": "Your message text",
  "timestamp": 1719000000000
}

// timestamp is optional (unix milliseconds)
// If omitted, the current time is used`}
              </pre>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Messages</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search messages..."
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-8"
              />
            </div>
            <Popover.Root>
              <Popover.Trigger
                className="flex h-8 items-center gap-1.5 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label="Filter by category"
              >
                <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="capitalize">{filterTriggerLabel()}</span>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </Popover.Trigger>
              <Popover.Portal>
                <Popover.Positioner sideOffset={4}>
                  <Popover.Popup className="z-50 min-w-[180px] rounded-lg border bg-popover p-1 text-popover-foreground ring-1 ring-foreground/10">
                    {selectedCategories.length > 0 && (
                      <div className="flex justify-end px-2 pb-1">
                        <button
                          onClick={clearCategoryFilter}
                          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                        >
                          <X className="h-3 w-3" />
                          Clear
                        </button>
                      </div>
                    )}
                    <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(0)}
                        onChange={() => toggleCategory(0)}
                        className="rounded"
                      />
                      <span className="h-2.5 w-2.5 rounded-full border-2 border-muted-foreground/40" />
                      <span>Uncategorized</span>
                    </label>
                    {categories.map((cat) => {
                      const color = getCategoryColor(cat.id);
                      return (
                        <label
                          key={cat.id}
                          className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                        >
                          <input
                            type="checkbox"
                            checked={selectedCategories.includes(cat.id)}
                            onChange={() => toggleCategory(cat.id)}
                            className="rounded"
                          />
                          <span
                            className={cn(
                              "h-2.5 w-2.5 rounded-full",
                              color.dot,
                            )}
                          />
                          <span className="capitalize">{cat.name}</span>
                        </label>
                      );
                    })}
                  </Popover.Popup>
                </Popover.Positioner>
              </Popover.Portal>
            </Popover.Root>
          </div>

          {!messages || messages.messages.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {hasFilter
                ? "No messages found"
                : "No messages yet. Configure your phone to send SMS to the webhook URL above."}
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {messages.messages.map((msg) => (
                <div
                  key={msg.id}
                  className="flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">
                        {msg.sender}
                      </span>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(msg.received_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground break-words">
                      {msg.content}
                    </p>
                    <div className="mt-2">
                      {msg.category ? (
                        <Badge
                          className={cn(
                            "capitalize",
                            getCategoryColor(msg.category.id).bg,
                            getCategoryColor(msg.category.id).text,
                            getCategoryColor(msg.category.id).ring,
                          )}
                        >
                          {msg.category.name}
                        </Badge>
                      ) : (
                        <Badge variant="muted">Uncategorized</Badge>
                      )}
                    </div>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger
                      render={
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label="Delete message"
                        />
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete message</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete this message? This
                          action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          variant="destructive"
                          onClick={() => handleDeleteMessage(msg.id)}
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
