import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import CategoriesPage from "@/pages/CategoriesPage";
import {
  mockFetch,
  mockFetchSequence,
  mockUser,
  renderWithOutletContext,
} from "@/test-utils";

const mockCategories = [
  { id: 1, name: "bills", created_at: "2026-01-01T00:00:00Z" },
  { id: 2, name: "groceries", created_at: "2026-01-02T00:00:00Z" },
];

function renderPage() {
  return renderWithOutletContext(<CategoriesPage />, { user: mockUser });
}

describe("CategoriesPage", () => {
  it("renders category list", async () => {
    mockFetch(200, mockCategories);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
    });
    expect(screen.getByText("groceries")).toBeInTheDocument();
  });

  it("shows empty state when no categories", async () => {
    mockFetch(200, []);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/no categories yet/i)).toBeInTheDocument();
    });
  });

  it("adds a new category", async () => {
    mockFetchSequence(
      { status: 200, body: [] },
      {
        status: 201,
        body: { id: 1, name: "travel", created_at: "2026-01-01T00:00:00Z" },
      },
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/no categories yet/i)).toBeInTheDocument();
    });

    await user.type(
      screen.getByPlaceholderText(/new category name/i),
      "travel",
    );
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(screen.getByText("travel")).toBeInTheDocument();
    });
  });

  it("shows error on duplicate category", async () => {
    mockFetchSequence(
      { status: 200, body: mockCategories },
      { status: 409, body: { detail: "Category already exists" } },
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText(/new category name/i), "bills");
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(screen.getByText("Category already exists")).toBeInTheDocument();
    });
  });

  it("edits a category inline", async () => {
    mockFetchSequence(
      { status: 200, body: mockCategories },
      {
        status: 200,
        body: { id: 1, name: "utilities", created_at: "2026-01-01T00:00:00Z" },
      },
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    const editInput = screen.getByDisplayValue("bills");
    await user.clear(editInput);
    await user.type(editInput, "utilities");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("utilities")).toBeInTheDocument();
    });
  });

  it("cancels editing", async () => {
    mockFetch(200, mockCategories);

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await user.click(editButtons[0]);

    expect(screen.getByDisplayValue("bills")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.getByText("bills")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("bills")).not.toBeInTheDocument();
  });

  it("deletes a category after confirmation", async () => {
    mockFetchSequence(
      { status: 200, body: mockCategories },
      { status: 200, body: { message: "Category deleted" } },
    );

    renderPage();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
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
      expect(screen.queryByText("bills")).not.toBeInTheDocument();
    });
    expect(screen.getByText("groceries")).toBeInTheDocument();
  });
});
