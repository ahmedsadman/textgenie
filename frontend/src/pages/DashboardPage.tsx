import { useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Popover } from "@base-ui/react/popover";

import { ChevronDown, Filter, Search, Trash2, X } from "lucide-react";

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
import PaginationNav from "@/components/PaginationNav";
import { useCategories } from "@/hooks/queries/useCategories";
import { useDeleteMessage, useMessages } from "@/hooks/queries/useMessages";
import type { User } from "@/lib/types";
import { cn, formatMessageDateTime, getCategoryColor } from "@/lib/utils";

const PAGE_SIZE = 5;

export default function DashboardPage() {
  const { user } = useOutletContext<{ user: User }>();

  const [page, setPage] = useState(1);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);

  const { data: categories = [] } = useCategories();
  const { data: messages, isPending } = useMessages({
    page,
    page_size: PAGE_SIZE,
    category_ids:
      selectedCategories.length > 0 ? selectedCategories : undefined,
    search: debouncedSearch.trim() || undefined,
  });
  const deleteMessage = useDeleteMessage();

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

  function handleDeleteMessage(messageId: number) {
    // If this was the only message on the current page, step back one after
    // the delete lands so the refetch doesn't leave an empty page.
    const wasOnlyOnPage =
      messages !== undefined && messages.messages.length === 1 && page > 1;
    deleteMessage.mutate(messageId, {
      onSuccess: () => {
        if (wasOnlyOnPage) setPage(page - 1);
      },
    });
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

          {isPending ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Loading messages...
            </p>
          ) : !messages || messages.messages.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {hasFilter
                ? "No messages found"
                : "No messages yet. Configure your phone to send SMS to the webhook URL on the Settings page."}
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
                        {formatMessageDateTime(msg.received_at)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground wrap-anywhere">
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

          <PaginationNav
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}
