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
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  totals: { income: "1500.00", expense: "250.00" },
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
