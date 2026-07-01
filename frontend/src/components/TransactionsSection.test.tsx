import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import TransactionsSection from "@/components/TransactionsSection";
import { server } from "@/mocks/server";
import { renderWithRouter } from "@/test-utils";

const sampleTransactions = {
  transactions: [
    {
      id: 1,
      message_id: 10,
      bank_id: 1,
      bank_name: "BRAC Bank",
      sender: "BRAC",
      amount: "1500.00",
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
      sender: "BRAC",
      amount: "250.00",
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
      sender: "MTB",
      amount: "2951.00",
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
      sender: "CITY",
      amount: "2951.00",
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

    renderWithRouter(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
    });
    // both sender rows render
    expect(screen.getAllByText("BRAC")).toHaveLength(2);
    // expense rendered with leading minus
    expect(screen.getByText(/−250\.00/)).toBeInTheDocument();
    // income rendered with leading plus
    expect(screen.getByText(/\+1,500\.00/)).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);

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

    renderWithRouter(<TransactionsSection />);

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

    renderWithRouter(<TransactionsSection />);
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getAllByText("2,951.00")).toHaveLength(2);
    });
    // No income/expense sign on transfer rows.
    expect(screen.queryByText(/[+−]2,951\.00/)).not.toBeInTheDocument();
  });

  it("shows the linked-pair icon on paired transfer rows", async () => {
    server.use(
      http.get("/api/transactions", () => HttpResponse.json(pairedTransfers)),
    );

    renderWithRouter(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getAllByText("2,951.00")).toHaveLength(2);
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

    renderWithRouter(<TransactionsSection />);

    await waitFor(() => {
      expect(screen.getByText("1,500.00")).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText(/linked transfer — paired/i),
    ).not.toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getAllByText("2,951.00")).toHaveLength(2);
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
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json(sampleTransactions),
      ),
      http.patch("/api/transactions/2", async ({ request }) => {
        receivedBody = (await request.json()) as { type: string };
        return HttpResponse.json({
          ...sampleTransactions.transactions[1],
          type: receivedBody.type,
        });
      }),
    );

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/−250\.00/)).toBeInTheDocument();
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
      expect(screen.queryByText(/−250\.00/)).not.toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/−250\.00/)).toBeInTheDocument();
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
    expect(screen.getByText(/−250\.00/)).toBeInTheDocument();
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

    renderWithRouter(<TransactionsSection />);
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
