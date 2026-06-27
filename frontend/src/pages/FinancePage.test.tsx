import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import FinancePage from "@/pages/FinancePage";
import { mockUser, renderWithOutletContext } from "@/test-utils";

const mockBanks = [
  {
    id: 1,
    name: "BRAC Bank",
    last_balance: "1500.00",
    last_balance_at: "2026-06-20T10:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "EBL",
    last_balance: null,
    last_balance_at: null,
    created_at: "2026-01-02T00:00:00Z",
  },
];

function renderPage() {
  return renderWithOutletContext(<FinancePage />, { user: mockUser });
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
    expect(screen.getAllByText("1,500.00")).toHaveLength(2);
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

  it("adds a new bank and refreshes the list", async () => {
    let createCalled = false;
    const newBank = {
      id: 1,
      name: "City Bank",
      last_balance: null,
      last_balance_at: null,
      created_at: "2026-06-24T00:00:00Z",
    };
    server.use(
      http.get("/api/banks", () =>
        HttpResponse.json(createCalled ? [newBank] : []),
      ),
      http.post("/api/banks", () => {
        createCalled = true;
        return HttpResponse.json(newBank, { status: 201 });
      }),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/no banks yet/i)).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText(/new bank name/i), "City Bank");
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(screen.getByText("City Bank")).toBeInTheDocument();
    });
  });

  it("shows error on duplicate bank", async () => {
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

    await user.type(screen.getByPlaceholderText(/new bank name/i), "BRAC Bank");
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(screen.getByText("Bank already exists")).toBeInTheDocument();
    });
  });

  it("edits a bank name inline", async () => {
    let putCalled = false;
    const renamed = {
      id: 1,
      name: "BRAC Bank PLC",
      last_balance: "1500.00",
      last_balance_at: "2026-06-20T10:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
    };
    server.use(
      http.put("/api/banks/1", () => {
        putCalled = true;
        return HttpResponse.json(renamed);
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(putCalled ? [renamed, mockBanks[1]] : mockBanks),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    const nameInput = screen.getByDisplayValue("BRAC Bank");
    await user.clear(nameInput);
    await user.type(nameInput, "BRAC Bank PLC");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank PLC")).toBeInTheDocument();
    });
  });

  it("edits a bank balance manually and updates total", async () => {
    let putCalled = false;
    const updated = {
      id: 2,
      name: "EBL",
      last_balance: "500.00",
      last_balance_at: "2026-06-24T00:00:00Z",
      created_at: "2026-01-02T00:00:00Z",
    };
    server.use(
      http.put("/api/banks/2", () => {
        putCalled = true;
        return HttpResponse.json(updated);
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(putCalled ? [mockBanks[0], updated] : mockBanks),
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("EBL")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[1]);

    const balanceInput = screen.getByPlaceholderText(/balance \(optional\)/i);
    await user.type(balanceInput, "500.00");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("2,000.00")).toBeInTheDocument();
    });
    expect(screen.getByText("500.00")).toBeInTheDocument();
  });

  it("cancels editing", async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    expect(screen.getByDisplayValue("BRAC Bank")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.getByText("BRAC Bank")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("BRAC Bank")).not.toBeInTheDocument();
  });

  it("deletes a bank after confirmation and refreshes total", async () => {
    let deleteCalled = false;
    server.use(
      http.delete("/api/banks/1", () => {
        deleteCalled = true;
        return HttpResponse.json({ message: "Bank deleted" });
      }),
      http.get("/api/banks", () =>
        HttpResponse.json(deleteCalled ? [mockBanks[1]] : mockBanks),
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
});
