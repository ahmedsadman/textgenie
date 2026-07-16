import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import BillsSection from "@/components/BillsSection";
import { server } from "@/mocks/server";
import { renderWithQueryClient } from "@/test-utils";
import type { Bank } from "@/lib/types";

const creditCard: Bank = {
  id: 1,
  name: "EBL Card",
  account_type: "credit",
  card_digits: "1234|5678",
  last_balance: null,
  last_balance_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const depositBank: Bank = {
  id: 2,
  name: "BRAC Bank",
  account_type: "deposit",
  card_digits: null,
  last_balance: "100000.00",
  last_balance_at: "2026-07-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
};

describe("BillsSection", () => {
  it("renders nothing when the user has no credit cards", () => {
    renderWithQueryClient(<BillsSection banks={[depositBank]} />);
    expect(screen.queryByText(/credit card bills/i)).not.toBeInTheDocument();
  });

  it("shows an empty state when a credit card has no bills", async () => {
    server.use(
      http.get("/api/bills", () =>
        HttpResponse.json({ bills: [], total: 0, page: 1, page_size: 20 }),
      ),
    );

    renderWithQueryClient(<BillsSection banks={[creditCard]} />);

    await waitFor(() => {
      expect(
        screen.getByText(/no bills yet for this card/i),
      ).toBeInTheDocument();
    });
  });

  it("renders a bill with amount, period, and Due badge", async () => {
    server.use(
      http.get("/api/bills", () =>
        HttpResponse.json({
          bills: [
            {
              id: 10,
              message_id: 500,
              sender: "EBL",
              received_at: "2026-07-01T09:00:00Z",
              bank_id: 1,
              bank_name: "EBL Card",
              normalized_total_due: "8020.00",
              normalized_currency: "BDT",
              original_amount: "8020.00",
              original_currency: "BDT",
              statement_period: "2026-07-01",
              paid_at: null,
              linked_transaction_ids: [],
              created_at: "2026-07-01T09:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      ),
    );

    renderWithQueryClient(<BillsSection banks={[creditCard]} />);

    await waitFor(() => {
      expect(screen.getByText(/8,020\.00\sBDT/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Jul\s2026/)).toBeInTheDocument();
    expect(screen.getByText(/Due/)).toBeInTheDocument();
  });

  it("shows Paid badge and Unlink action when a payment is linked", async () => {
    const user = userEvent.setup();
    let unlinkedIds: number[] | null = null;

    server.use(
      http.get("/api/bills", () =>
        HttpResponse.json({
          bills: [
            {
              id: 11,
              message_id: 501,
              sender: "EBL",
              received_at: "2026-07-01T09:00:00Z",
              bank_id: 1,
              bank_name: "EBL Card",
              normalized_total_due: "500.00",
              normalized_currency: "BDT",
              original_amount: "500.00",
              original_currency: "BDT",
              statement_period: "2026-07-01",
              paid_at: "2026-07-05T09:00:00Z",
              linked_transaction_ids: [77],
              created_at: "2026-07-01T09:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      ),
      http.patch("/api/bills/:id", async ({ request, params }) => {
        const body = (await request.json()) as {
          unlink_transaction_ids: number[];
        };
        unlinkedIds = body.unlink_transaction_ids;
        return HttpResponse.json({
          id: Number(params.id),
          message_id: 501,
          sender: "EBL",
          received_at: "2026-07-01T09:00:00Z",
          bank_id: 1,
          bank_name: "EBL Card",
          normalized_total_due: "500.00",
          normalized_currency: "BDT",
          original_amount: "500.00",
          original_currency: "BDT",
          statement_period: "2026-07-01",
          paid_at: null,
          linked_transaction_ids: [],
          created_at: "2026-07-01T09:00:00Z",
        });
      }),
    );

    renderWithQueryClient(<BillsSection banks={[creditCard]} />);

    await waitFor(() => {
      expect(screen.getByText("Paid")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText(/unlink payment/i));
    await user.click(screen.getByRole("button", { name: /^unlink$/i }));

    await waitFor(() => {
      expect(unlinkedIds).toEqual([77]);
    });
  });

  it("does not show the unlink action when no payment is linked", async () => {
    server.use(
      http.get("/api/bills", () =>
        HttpResponse.json({
          bills: [
            {
              id: 12,
              message_id: 502,
              sender: "EBL",
              received_at: "2026-07-01T09:00:00Z",
              bank_id: 1,
              bank_name: "EBL Card",
              normalized_total_due: "500.00",
              normalized_currency: "BDT",
              original_amount: "500.00",
              original_currency: "BDT",
              statement_period: "2026-07-01",
              paid_at: null,
              linked_transaction_ids: [],
              created_at: "2026-07-01T09:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      ),
    );

    renderWithQueryClient(<BillsSection banks={[creditCard]} />);

    await waitFor(() => {
      expect(screen.getByText(/500\.00\sBDT/)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/unlink payment/i)).not.toBeInTheDocument();
  });
});
