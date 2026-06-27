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
