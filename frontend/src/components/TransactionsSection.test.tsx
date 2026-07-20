import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import TransactionsSection from "@/components/TransactionsSection";
import { server } from "@/mocks/server";
import { renderWithQueryClient } from "@/test-utils";

const sampleTransactions = {
  transactions: [
    {
      id: 1,
      message_id: 10,
      bank_id: 1,
      bank_name: "BRAC Bank",
      bank_account_type: "deposit" as const,
      sender: "BRAC",
      normalized_amount: "1500.00",
      normalized_currency: "BDT" as const,
      original_amount: null,
      original_currency: null,
      type: "income" as const,
      date: "2026-06-20T10:00:00Z",
      paired_with_id: null,
      paired_with_message_id: null,
    },
    {
      id: 2,
      message_id: 11,
      bank_id: 1,
      bank_name: "BRAC Bank",
      bank_account_type: "deposit" as const,
      sender: "BRAC",
      normalized_amount: "250.00",
      normalized_currency: "BDT" as const,
      original_amount: null,
      original_currency: null,
      type: "expense" as const,
      date: "2026-06-19T10:00:00Z",
      paired_with_id: null,
      paired_with_message_id: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  totals: { income: "1500.00", expense: "250.00" },
};

const pairedTransfers = {
  transactions: [
    {
      id: 100,
      message_id: 200,
      bank_id: 1,
      bank_name: "MTB",
      bank_account_type: "deposit" as const,
      sender: "MTB",
      normalized_amount: "2951.00",
      normalized_currency: "BDT" as const,
      original_amount: null,
      original_currency: null,
      type: "transfer" as const,
      date: "2026-06-20T10:00:00Z",
      paired_with_id: 101,
      paired_with_message_id: 201,
    },
    {
      id: 101,
      message_id: 201,
      bank_id: 2,
      bank_name: "City Bank",
      bank_account_type: "deposit" as const,
      sender: "CITY",
      normalized_amount: "2951.00",
      normalized_currency: "BDT" as const,
      original_amount: null,
      original_currency: null,
      type: "transfer" as const,
      date: "2026-06-20T10:02:00Z",
      paired_with_id: 100,
      paired_with_message_id: 200,
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  totals: { income: "0.00", expense: "0.00" },
};

describe("TransactionsSection", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders totals and a list of transactions", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });
    // both sender rows render
    expect(screen.getAllByText("BRAC")).toHaveLength(2);
    // expense rendered with leading minus
    expect(screen.getByText(/−250\.00\sBDT/)).toBeInTheDocument();
    // (leading-plus income asserted above)
  });

  it("shows empty state when there are no transactions", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(
        screen.getByText(/no transactions in this range/i),
      ).toBeInTheDocument();
    });
  });

  it("sends a from_date for the default Last month preset", async () => {
    let receivedParams: URLSearchParams | null = null;
    server.use(
      http.get("/api/transactions", ({ request }) => {
        receivedParams = new URL(request.url).searchParams;
        return HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(receivedParams).not.toBeNull();
    });
    expect(receivedParams!.get("from_date")).not.toBeNull();
    expect(receivedParams!.get("to_date")).not.toBeNull();
  });

  it("omits date params when 'All time' preset is chosen", async () => {
    const calls: URLSearchParams[] = [];
    server.use(
      http.get("/api/transactions", ({ request }) => {
        calls.push(new URL(request.url).searchParams);
        return HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => expect(calls.length).toBeGreaterThan(0));

    await user.click(
      screen.getByRole("button", { name: /select date range/i }),
    );
    await user.click(screen.getByText("All time"));

    await waitFor(() => expect(calls.length).toBeGreaterThan(1));
    const last = calls[calls.length - 1];
    expect(last.get("from_date")).toBeNull();
    expect(last.get("to_date")).toBeNull();
  });

  it("expands a transaction row to show its source message", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.get("/api/messages/10", () =>
        HttpResponse.json({
          id: 10,
          sender: "BRAC",
          content: "You received Tk 1500 in your account",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    const firstRow = screen.getAllByRole("button", {
      name: /toggle message for brac/i,
    })[0];
    await user.click(firstRow);

    expect(
      await screen.findByText("You received Tk 1500 in your account"),
    ).toBeInTheDocument();
    expect(firstRow).toHaveAttribute("aria-expanded", "true");
  });

  it("collapses a transaction row when toggled again", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.get("/api/messages/10", () =>
        HttpResponse.json({
          id: 10,
          sender: "BRAC",
          content: "Source message body",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    const row = screen.getAllByRole("button", {
      name: /toggle message for brac/i,
    })[0];

    await user.click(row);
    expect(await screen.findByText("Source message body")).toBeInTheDocument();

    await user.click(row);
    await waitFor(() => {
      expect(screen.queryByText("Source message body")).not.toBeInTheDocument();
    });
  });

  it("does not refetch a message that is already cached", async () => {
    let messageCallCount = 0;
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.get("/api/messages/10", () => {
        messageCallCount += 1;
        return HttpResponse.json({
          id: 10,
          sender: "BRAC",
          content: "Cached message body",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    const row = screen.getAllByRole("button", {
      name: /toggle message for brac/i,
    })[0];

    await user.click(row);
    expect(await screen.findByText("Cached message body")).toBeInTheDocument();

    await user.click(row); // collapse
    await waitFor(() => {
      expect(screen.queryByText("Cached message body")).not.toBeInTheDocument();
    });

    await user.click(row); // re-expand
    expect(await screen.findByText("Cached message body")).toBeInTheDocument();

    expect(messageCallCount).toBe(1);
  });

  it("expands two rows independently and shows each message", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.get("/api/messages/10", () =>
        HttpResponse.json({
          id: 10,
          sender: "BRAC",
          content: "Income message",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        }),
      ),
      http.get("/api/messages/11", () =>
        HttpResponse.json({
          id: 11,
          sender: "BRAC",
          content: "Expense message",
          received_at: "2026-06-19T10:00:00Z",
          category: null,
          created_at: "2026-06-19T10:00:00Z",
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("button", {
      name: /toggle message for brac/i,
    });

    await user.click(rows[0]);
    await user.click(rows[1]);

    expect(await screen.findByText("Income message")).toBeInTheDocument();
    expect(await screen.findByText("Expense message")).toBeInTheDocument();
  });

  it("shows an error with retry when message fetch fails, then recovers", async () => {
    let attempt = 0;
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.get("/api/messages/10", () => {
        attempt += 1;
        if (attempt === 1) {
          return new HttpResponse(null, { status: 500 });
        }
        return HttpResponse.json({
          id: 10,
          sender: "BRAC",
          content: "Recovered message body",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    const row = screen.getAllByRole("button", {
      name: /toggle message for brac/i,
    })[0];
    await user.click(row);

    const retryButton = await screen.findByRole("button", { name: /retry/i });
    await user.click(retryButton);

    expect(
      await screen.findByText("Recovered message body"),
    ).toBeInTheDocument();
  });

  it("renders transfer rows without a +/- sign and in neutral color", async () => {
    server.use(
      http.get("/api/transactions", () => HttpResponse.json(pairedTransfers)),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getAllByText(/2,951\.00\sBDT/)).toHaveLength(2);
    });
    // No income/expense sign on transfer rows.
    expect(screen.queryByText(/[+−]2,951\.00\sBDT/)).not.toBeInTheDocument();
  });

  it("shows the linked-pair icon on paired transfer rows", async () => {
    server.use(
      http.get("/api/transactions", () => HttpResponse.json(pairedTransfers)),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getAllByText(/2,951\.00\sBDT/)).toHaveLength(2);
    });
    expect(screen.getAllByLabelText(/linked transfer — paired/i)).toHaveLength(
      2,
    );
  });

  it("does not show the link icon on unpaired rows", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText(/linked transfer — paired/i),
    ).not.toBeInTheDocument();
  });

  it("shows the receipt icon on transactions linked to a bill", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [
            {
              id: 500,
              message_id: 600,
              bank_id: 3,
              bank_name: "EBL Card",
              bank_account_type: "credit" as const,
              sender: "EBL",
              normalized_amount: "8020.00",
              normalized_currency: "BDT" as const,
              original_amount: null,
              original_currency: null,
              type: "transfer" as const,
              date: "2026-07-05T10:00:00Z",
              paired_with_id: null,
              paired_with_message_id: null,
              bill_id: 42,
            },
          ],
          total: 1,
          page: 1,
          page_size: 10,
          totals: { income: "0.00", expense: "0.00" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText(/8,020\.00\sBDT/)).toBeInTheDocument();
    });
    expect(
      screen.getByLabelText(/linked to a credit card bill/i),
    ).toBeInTheDocument();
  });

  it("expands a paired row and shows both source SMS messages", async () => {
    server.use(
      http.get("/api/transactions", () => HttpResponse.json(pairedTransfers)),
      http.get("/api/messages/200", () =>
        HttpResponse.json({
          id: 200,
          sender: "MTB",
          content: "Payment of 2951 credited to your card 1234",
          received_at: "2026-06-20T10:00:00Z",
          category: null,
          created_at: "2026-06-20T10:00:00Z",
        }),
      ),
      http.get("/api/messages/201", () =>
        HttpResponse.json({
          id: 201,
          sender: "CITY",
          content: "Acct debit 2951 BDT. Bal 50000",
          received_at: "2026-06-20T10:02:00Z",
          category: null,
          created_at: "2026-06-20T10:02:00Z",
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getAllByText(/2,951\.00\sBDT/)).toHaveLength(2);
    });

    const firstRow = screen.getAllByRole("button", {
      name: /toggle message for mtb/i,
    })[0];
    await user.click(firstRow);

    expect(
      await screen.findByText("Payment of 2951 credited to your card 1234"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Acct debit 2951 BDT. Bal 50000"),
    ).toBeInTheDocument();
  });

  it("updates a transaction's type via the dropdown", async () => {
    let receivedBody: { type: string } | null = null;
    let currentType: "expense" | "income" | "transfer" = "expense";
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          ...sampleTransactions,
          transactions: [
            sampleTransactions.transactions[0],
            { ...sampleTransactions.transactions[1], type: currentType },
          ],
        }),
      ),
      http.patch("/api/transactions/2", async ({ request }) => {
        receivedBody = (await request.json()) as { type: string };
        currentType = receivedBody.type as typeof currentType;
        return HttpResponse.json({
          ...sampleTransactions.transactions[1],
          type: currentType,
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/−250\.00\sBDT/)).toBeInTheDocument();
    });

    const triggers = screen.getAllByRole("button", {
      name: /change transaction type/i,
    });
    // sampleTransactions order: income (id=1) then expense (id=2)
    await user.click(triggers[1]);
    await user.click(
      await screen.findByRole("button", { name: /^transfer$/i }),
    );

    await waitFor(() => expect(receivedBody).toEqual({ type: "transfer" }));
    // After flipping to transfer, the row no longer renders with a "−" sign.
    await waitFor(() => {
      expect(screen.queryByText(/−250\.00\sBDT/)).not.toBeInTheDocument();
    });
    // The trigger button's accessible name reflects the new type.
    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: /change transaction type \(currently transfer\)/i,
        }),
      ).toBeInTheDocument();
    });
  });

  it("rolls back the optimistic update and shows a toast when PATCH fails", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.patch("/api/transactions/2", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/−250\.00\sBDT/)).toBeInTheDocument();
    });

    const triggers = screen.getAllByRole("button", {
      name: /change transaction type/i,
    });
    await user.click(triggers[1]);
    await user.click(await screen.findByRole("button", { name: /^income$/i }));

    // Toast surfaces the failure.
    expect(
      await screen.findByText(/failed to update transaction/i),
    ).toBeInTheDocument();
    // Row is restored to its original expense rendering.
    expect(screen.getByText(/−250\.00\sBDT/)).toBeInTheDocument();
  });

  it("shows a Credit indicator for credit-account transactions only", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [
            {
              id: 1,
              message_id: 10,
              bank_id: 1,
              bank_name: "BRAC Bank",
              bank_account_type: "deposit" as const,
              sender: "BRAC",
              normalized_amount: "100.00",
              normalized_currency: "BDT" as const,
              original_amount: null,
              original_currency: null,
              type: "expense" as const,
              date: "2026-06-20T10:00:00Z",
              paired_with_id: null,
              paired_with_message_id: null,
            },
            {
              id: 2,
              message_id: 11,
              bank_id: 2,
              bank_name: "Amex Card",
              bank_account_type: "credit" as const,
              sender: "AMEX",
              normalized_amount: "200.00",
              normalized_currency: "BDT" as const,
              original_amount: null,
              original_currency: null,
              type: "expense" as const,
              date: "2026-06-19T10:00:00Z",
              paired_with_id: null,
              paired_with_message_id: null,
            },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          totals: { income: "0.00", expense: "300.00" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getAllByText(/Amex Card/).length).toBeGreaterThan(0);
    });
    // Only the credit row shows the desktop badge.
    const badges = screen.getAllByText("Credit");
    expect(badges).toHaveLength(1);
    // The deposit row's bank name is present without any Credit indicator.
    expect(screen.getAllByText(/BRAC Bank/).length).toBeGreaterThan(0);
  });

  it("renders each row with its own currency label", async () => {
    // Mixed currencies arise after a preference change: older rows keep their
    // previous normalized currency; newer rows use the current one.
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [
            {
              id: 1,
              message_id: 10,
              bank_id: 1,
              bank_name: "BRAC",
              bank_account_type: "deposit" as const,
              sender: "BRAC",
              normalized_amount: "1500.00",
              normalized_currency: "USD" as const,
              original_amount: "180000.00",
              original_currency: "BDT",
              type: "income" as const,
              date: "2026-06-20T10:00:00Z",
              paired_with_id: null,
              paired_with_message_id: null,
            },
            {
              id: 2,
              message_id: 11,
              bank_id: 1,
              bank_name: "BRAC",
              bank_account_type: "deposit" as const,
              sender: "BRAC",
              normalized_amount: "250.00",
              normalized_currency: "BDT" as const,
              original_amount: "250.00",
              original_currency: "BDT",
              type: "expense" as const,
              date: "2026-06-19T10:00:00Z",
              paired_with_id: null,
              paired_with_message_id: null,
            },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          totals: { income: "1500.00", expense: "250.00" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sUSD/)).toBeInTheDocument();
    });
    expect(screen.getByText(/−250\.00\sBDT/)).toBeInTheDocument();
  });

  it("sends selected types as repeated params when the type filter is used", async () => {
    const calls: URLSearchParams[] = [];
    server.use(
      http.get("/api/transactions", ({ request }) => {
        calls.push(new URL(request.url).searchParams);
        return HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => expect(calls.length).toBeGreaterThan(0));
    // Default: no types param sent.
    expect(calls[0].getAll("types")).toEqual([]);

    await user.click(screen.getByRole("button", { name: /filter by type/i }));
    await user.click(await screen.findByRole("button", { name: /^expense$/i }));

    await waitFor(() => expect(calls.length).toBeGreaterThan(1));
    const last = calls[calls.length - 1];
    expect(last.getAll("types")).toEqual(["expense"]);
  });

  it("selecting all three types drops the filter param", async () => {
    const calls: URLSearchParams[] = [];
    server.use(
      http.get("/api/transactions", ({ request }) => {
        calls.push(new URL(request.url).searchParams);
        return HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => expect(calls.length).toBeGreaterThan(0));

    await user.click(screen.getByRole("button", { name: /filter by type/i }));
    await user.click(await screen.findByRole("button", { name: /^expense$/i }));
    await user.click(await screen.findByRole("button", { name: /^income$/i }));
    await user.click(
      await screen.findByRole("button", { name: /^transfer$/i }),
    );

    await waitFor(() => {
      const last = calls[calls.length - 1];
      expect(last.getAll("types")).toEqual([]);
    });
  });

  it("totals cards keep their values when the type filter changes", async () => {
    const consistentTotals = { income: "1500.00", expense: "250.00" };
    server.use(
      http.get("/api/transactions", ({ request }) => {
        const params = new URL(request.url).searchParams;
        const types = params.getAll("types");
        const filtered =
          types.length === 0
            ? sampleTransactions.transactions
            : sampleTransactions.transactions.filter((t) =>
                types.includes(t.type),
              );
        return HttpResponse.json({
          transactions: filtered,
          total: filtered.length,
          page: 1,
          page_size: 10,
          // Backend keeps totals scoped to the date range (not the filter).
          totals: consistentTotals,
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/\+1,500\.00\sBDT/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /filter by type/i }));
    await user.click(await screen.findByRole("button", { name: /^expense$/i }));

    // Income row disappears, but the Income totals card still shows 1,500.00.
    await waitFor(() => {
      expect(screen.queryByText(/\+1,500\.00\sBDT/)).not.toBeInTheDocument();
    });
    expect(screen.getByText("1,500.00")).toBeInTheDocument();
    expect(screen.getByText("250.00")).toBeInTheDocument();
  });

  it("sends sort_by=amount and sort_dir=asc when Lowest amount is selected", async () => {
    const calls: URLSearchParams[] = [];
    server.use(
      http.get("/api/transactions", ({ request }) => {
        calls.push(new URL(request.url).searchParams);
        return HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        });
      }),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => expect(calls.length).toBeGreaterThan(0));
    // Default sort.
    expect(calls[0].get("sort_by")).toBe("date");
    expect(calls[0].get("sort_dir")).toBe("desc");

    await user.click(
      screen.getByRole("button", { name: /sort transactions/i }),
    );
    await user.click(
      await screen.findByRole("button", { name: /lowest amount/i }),
    );

    await waitFor(() => {
      const last = calls[calls.length - 1];
      expect(last.get("sort_by")).toBe("amount");
      expect(last.get("sort_dir")).toBe("asc");
    });
  });

  it("persists the type filter and sort selection to localStorage", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /filter by type/i }));
    await user.click(await screen.findByRole("button", { name: /^income$/i }));

    await user.click(
      screen.getByRole("button", { name: /sort transactions/i }),
    );
    await user.click(
      await screen.findByRole("button", { name: /highest amount/i }),
    );

    await waitFor(() => {
      expect(JSON.parse(localStorage.getItem("finance.txTypes") ?? "")).toEqual(
        ["income"],
      );
      expect(localStorage.getItem("finance.txSort")).toBe('"amount-desc"');
    });
  });

  it("persists the selected preset to localStorage", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [],
          total: 0,
          page: 1,
          page_size: 10,
          totals: { income: "0", expense: "0" },
        }),
      ),
    );

    renderWithQueryClient(<TransactionsSection />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /select date range/i }),
    );
    await user.click(screen.getByText("Last 7 days"));

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem("finance.txRange") ?? "");
      expect(stored.presetKey).toBe("last_7_days");
    });
  });
});
