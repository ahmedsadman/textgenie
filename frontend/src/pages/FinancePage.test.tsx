import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import FinancePage from "@/pages/FinancePage";
import { mockUser, renderWithQueryClientAndOutletContext } from "@/test-utils";

const mockBanks = [
  {
    id: 1,
    name: "BRAC Bank",
    account_type: "deposit",
    card_digits: null,
    last_balance: "1500.00",
    last_balance_at: "2026-06-20T10:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "EBL",
    account_type: "deposit",
    card_digits: null,
    last_balance: null,
    last_balance_at: null,
    created_at: "2026-01-02T00:00:00Z",
  },
];

function renderPage() {
  return renderWithQueryClientAndOutletContext(<FinancePage />, {
    user: mockUser,
  });
}

const emptyTransactions = {
  transactions: [],
  total: 0,
  page: 1,
  page_size: 10,
  totals: { income: "0", expense: "0" },
};

describe("FinancePage", () => {
  beforeEach(() => {
    localStorage.clear();
    server.use(
      http.get("/api/banks", () => HttpResponse.json(mockBanks)),
      http.get("/api/transactions", () => HttpResponse.json(emptyTransactions)),
    );
  });

  it("renders bank list with total balance", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });
    expect(screen.getByText("EBL")).toBeInTheDocument();
    // 1,500.00 appears twice: once as the bank's balance, once as the total.
    expect(screen.getAllByText(/1,500\.00\sBDT/)).toHaveLength(2);
    expect(screen.getByText(/total balance/i)).toBeInTheDocument();
  });

  it("shows 'No balance yet' for banks without a balance", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("EBL")).toBeInTheDocument();
    });
    expect(screen.getByText(/no balance yet/i)).toBeInTheDocument();
  });

  it("shows empty state when no banks", async () => {
    server.use(http.get("/api/banks", () => HttpResponse.json([])));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/no banks yet/i)).toBeInTheDocument();
    });
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("adds a new bank via the modal", async () => {
    let createCalled = false;
    const newBank = {
      id: 3,
      name: "City Bank",
      account_type: "deposit",
      card_digits: null,
      last_balance: null,
      last_balance_at: null,
      created_at: "2026-06-24T00:00:00Z",
    };
    server.use(
      http.get("/api/banks", () =>
        HttpResponse.json(createCalled ? [...mockBanks, newBank] : mockBanks),
      ),
      http.post("/api/banks", () => {
        createCalled = true;
        return HttpResponse.json(newBank, { status: 201 });
      }),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /add bank/i }));
    await screen.findByRole("heading", { name: /add bank/i });

    await user.type(screen.getByLabelText(/name/i), "City Bank");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => {
      expect(screen.getByText("City Bank")).toBeInTheDocument();
    });
    // Modal closed after successful submit.
    expect(
      screen.queryByRole("heading", { name: /add bank/i }),
    ).not.toBeInTheDocument();
  });

  it("shows error on duplicate bank without closing the modal", async () => {
    server.use(
      http.post("/api/banks", () =>
        HttpResponse.json({ detail: "Bank already exists" }, { status: 409 }),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /add bank/i }));
    await user.type(screen.getByLabelText(/name/i), "BRAC Bank");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => {
      expect(screen.getByText("Bank already exists")).toBeInTheDocument();
    });
    // Modal stays open so the user can fix the name.
    expect(
      screen.getByRole("heading", { name: /add bank/i }),
    ).toBeInTheDocument();
  });

  it("edits a bank name via the modal", async () => {
    let patched = false;
    const renamed = {
      ...mockBanks[0],
      name: "BRAC Bank PLC",
    };
    server.use(
      http.patch("/api/banks/1", () => {
        patched = true;
        return HttpResponse.json(renamed);
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(patched ? [renamed, mockBanks[1]] : mockBanks),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    await screen.findByRole("heading", { name: /edit bank/i });
    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "BRAC Bank PLC");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank PLC")).toBeInTheDocument();
    });
  });

  it("edits a bank balance via the modal and updates the total", async () => {
    let patched = false;
    const updated = {
      ...mockBanks[1],
      last_balance: "500.00",
      last_balance_at: "2026-06-24T00:00:00Z",
    };
    server.use(
      http.patch("/api/banks/2", () => {
        patched = true;
        return HttpResponse.json(updated);
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(patched ? [mockBanks[0], updated] : mockBanks),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("EBL")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[1]);

    await screen.findByRole("heading", { name: /edit bank/i });
    const balanceInput = screen.getByLabelText(/balance/i);
    await user.type(balanceInput, "500.00");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("2,000.00 BDT")).toBeInTheDocument();
    });
    expect(screen.getByText("500.00 BDT")).toBeInTheDocument();
  });

  it("cancels the modal without saving", async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    await screen.findByRole("heading", { name: /edit bank/i });
    expect(screen.getByDisplayValue("BRAC Bank")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /cancel/i }));

    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { name: /edit bank/i }),
      ).not.toBeInTheDocument();
    });
    // Original bank name is still on the card.
    expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
  });

  it("deletes a bank after confirmation and refreshes the list", async () => {
    let deleted = false;
    server.use(
      http.delete("/api/banks/1", () => {
        deleted = true;
        return HttpResponse.json({ message: "Bank deleted" });
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(deleted ? [mockBanks[1]] : mockBanks),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText(/are you sure you want to delete/i),
      ).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole("button", { name: /^delete$/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(screen.queryByText("BRAC Bank")).not.toBeInTheDocument();
    });
    expect(screen.getByText("EBL")).toBeInTheDocument();
  });

  it("shows a Credit badge and hides balance for credit accounts", async () => {
    const creditBank = {
      id: 3,
      name: "BRAC Credit Card",
      account_type: "credit",
      card_digits: "4988|3711",
      last_balance: null,
      last_balance_at: null,
      created_at: "2026-06-24T00:00:00Z",
    };
    server.use(
      http.get("/api/banks", () =>
        HttpResponse.json([mockBanks[0], creditBank]),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("BRAC Credit Card")).toBeInTheDocument();
    });
    expect(screen.getByText("Credit")).toBeInTheDocument();
    expect(screen.getByText(/•••• 3711/)).toBeInTheDocument();
    expect(screen.getByText(/not counted in total/i)).toBeInTheDocument();
    // Only the deposit bank's balance appears (once as its balance, once in total).
    expect(screen.getAllByText(/1,500\.00\sBDT/)).toHaveLength(2);
  });

  it("creates a credit account with card digits via the modal", async () => {
    let created = false;
    const newCredit = {
      id: 3,
      name: "City Credit Card",
      account_type: "credit",
      card_digits: "4988|3711",
      last_balance: null,
      last_balance_at: null,
      created_at: "2026-07-03T00:00:00Z",
    };
    server.use(
      http.get("/api/banks", () =>
        HttpResponse.json(created ? [...mockBanks, newCredit] : mockBanks),
      ),
      http.post("/api/banks", () => {
        created = true;
        return HttpResponse.json(newCredit, { status: 201 });
      }),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /add bank/i }));
    await screen.findByRole("heading", { name: /add bank/i });

    await user.type(screen.getByLabelText(/name/i), "City Credit Card");
    await user.click(
      screen.getByRole("checkbox", { name: /credit card account/i }),
    );
    await user.type(screen.getByLabelText(/card first 4 digits/i), "4988");
    await user.type(screen.getByLabelText(/card last 4 digits/i), "3711");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    // The credit card appears in the list with the Credit badge — proof that the
    // submit sent account_type=credit and the API accepted it.
    await waitFor(() => {
      expect(screen.getByText("City Credit Card")).toBeInTheDocument();
    });
    expect(screen.getByText("Credit")).toBeInTheDocument();
    expect(screen.getByText(/•••• 3711/)).toBeInTheDocument();
  });

  it("toggling credit in the edit modal hides the balance input and shows card inputs", async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    await screen.findByRole("heading", { name: /edit bank/i });
    // Balance input is visible while account is deposit.
    expect(screen.getByLabelText(/balance/i)).toBeInTheDocument();

    // Toggle credit — balance input goes away, card-digit inputs appear.
    await user.click(
      screen.getByRole("checkbox", { name: /credit card account/i }),
    );

    expect(screen.queryByLabelText(/balance/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/card first 4 digits/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/card last 4 digits/i)).toBeInTheDocument();
  });

  it("shows the credit-account explainer tooltip on hover", async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /add bank/i }));
    await screen.findByRole("heading", { name: /add bank/i });

    await user.hover(
      screen.getByRole("button", { name: /what is a credit card account/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(/report a limit, not real money/i),
      ).toBeInTheDocument();
    });
  });

  it("resets the form when reopening in create mode after editing a bank", async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    // Open in edit mode — form is prefilled with BRAC Bank.
    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);
    await screen.findByRole("heading", { name: /edit bank/i });
    expect(screen.getByDisplayValue("BRAC Bank")).toBeInTheDocument();

    // Close it.
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { name: /edit bank/i }),
      ).not.toBeInTheDocument();
    });

    // Reopen in create mode — name is blank.
    await user.click(screen.getByRole("button", { name: /add bank/i }));
    await screen.findByRole("heading", { name: /add bank/i });
    expect(screen.getByLabelText(/name/i)).toHaveValue("");
  });
});
