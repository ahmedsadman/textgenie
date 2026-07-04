import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import CategoriesSection from "@/components/CategoriesSection";
import { server } from "@/mocks/server";
import { renderWithQueryClient } from "@/test-utils";

const mockCategories = [
  {
    id: 1,
    name: "bills",
    is_default: false,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "groceries",
    is_default: false,
    created_at: "2026-01-02T00:00:00Z",
  },
  {
    id: 3,
    name: "transaction",
    is_default: true,
    created_at: "2026-01-01T00:00:00Z",
  },
];

function renderSection() {
  return renderWithQueryClient(<CategoriesSection />);
}

describe("CategoriesSection", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/categories", () => HttpResponse.json(mockCategories)),
    );
  });

  it("renders category list", async () => {
    renderSection();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
    });
    expect(screen.getByText("groceries")).toBeInTheDocument();
  });

  it("shows empty state when no categories", async () => {
    server.use(http.get("/api/categories", () => HttpResponse.json([])));

    renderSection();

    await waitFor(() => {
      expect(screen.getByText(/no categories yet/i)).toBeInTheDocument();
    });
  });

  it("adds a new category", async () => {
    let created = false;
    const newCategory = {
      id: 10,
      name: "travel",
      is_default: false,
      created_at: "2026-01-01T00:00:00Z",
    };
    server.use(
      http.get("/api/categories", () =>
        HttpResponse.json(
          created ? [...mockCategories, newCategory] : mockCategories,
        ),
      ),
      http.post("/api/categories", () => {
        created = true;
        return HttpResponse.json(newCategory, { status: 201 });
      }),
    );

    renderSection();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("bills")).toBeInTheDocument();
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
    server.use(
      http.post("/api/categories", () =>
        HttpResponse.json(
          { detail: "Category already exists" },
          { status: 409 },
        ),
      ),
    );

    renderSection();
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
    let updated = false;
    const renamed = { ...mockCategories[0], name: "utilities" };
    server.use(
      http.get("/api/categories", () =>
        HttpResponse.json(
          updated
            ? [renamed, mockCategories[1], mockCategories[2]]
            : mockCategories,
        ),
      ),
      http.put("/api/categories/1", () => {
        updated = true;
        return HttpResponse.json(renamed);
      }),
    );

    renderSection();
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
    renderSection();
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
    let deleted = false;
    server.use(
      http.get("/api/categories", () =>
        HttpResponse.json(
          deleted ? [mockCategories[1], mockCategories[2]] : mockCategories,
        ),
      ),
      http.delete("/api/categories/1", () => {
        deleted = true;
        return HttpResponse.json({ message: "Category deleted" });
      }),
    );

    renderSection();
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

  it("does not show edit/delete buttons for default categories", async () => {
    renderSection();

    await waitFor(() => {
      expect(screen.getByText("transaction")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });

    expect(editButtons).toHaveLength(2);
    expect(deleteButtons).toHaveLength(2);
  });
});
