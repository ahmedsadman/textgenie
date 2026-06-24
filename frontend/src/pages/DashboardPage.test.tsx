import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import DashboardPage from "@/pages/DashboardPage";
import { mockUser, renderWithOutletContext } from "@/test-utils";

const mockWebhook = {
  webhook_url: "http://localhost:8001/api/webhook/test-token-123",
  webhook_token: "test-token-123",
};

const mockCategories = [
  { id: 1, name: "finance", created_at: "2026-01-01T00:00:00Z" },
  { id: 2, name: "personal", created_at: "2026-01-01T00:00:00Z" },
];

const mockMessages = {
  messages: [
    {
      id: 1,
      sender: "Bank",
      content: "You paid $50",
      received_at: "2026-06-21T10:00:00Z",
      category: { id: 1, name: "finance", created_at: "2026-01-01T00:00:00Z" },
      created_at: "2026-06-21T10:00:00Z",
    },
    {
      id: 2,
      sender: "Mom",
      content: "Happy birthday",
      received_at: "2026-06-21T11:00:00Z",
      category: null,
      created_at: "2026-06-21T11:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 5,
};

const emptyMessages = { messages: [], total: 0, page: 1, page_size: 20 };

function renderDashboard() {
  return renderWithOutletContext(<DashboardPage />, { user: mockUser });
}

describe("DashboardPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/settings/webhook", () => HttpResponse.json(mockWebhook)),
      http.get("/api/categories", () => HttpResponse.json(mockCategories)),
      http.get("/api/messages", () => HttpResponse.json(mockMessages)),
    );
  });

  it("shows dashboard title and welcome", async () => {
    renderDashboard();
    await screen.findByText("Dashboard");
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
  });

  it("displays webhook URL", async () => {
    renderDashboard();
    await screen.findByDisplayValue(mockWebhook.webhook_url);
  });

  it("copies webhook URL to clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
      configurable: true,
    });

    renderDashboard();
    await screen.findByDisplayValue(mockWebhook.webhook_url);

    await user.click(screen.getByLabelText("Copy webhook URL"));
    expect(writeText).toHaveBeenCalledWith(mockWebhook.webhook_url);
  });

  it("shows setup instructions when expanded", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByText("Setup Instructions");

    await user.click(screen.getByText("Setup Instructions"));
    expect(
      screen.getByText(/Content-Type: application\/json/),
    ).toBeInTheDocument();
  });

  it("renders message list", async () => {
    renderDashboard();
    await screen.findByText("Bank");
    expect(screen.getByText("You paid $50")).toBeInTheDocument();
    expect(screen.getByText("Mom")).toBeInTheDocument();
    expect(screen.getByText("Happy birthday")).toBeInTheDocument();
  });

  it("shows color-coded category badge on categorized messages", async () => {
    renderDashboard();
    const badge = await screen.findByText("finance", {
      selector: "[data-slot='badge']",
    });
    expect(badge.className).toMatch(/bg-/);
    expect(
      screen.getByText("Uncategorized", { selector: "[data-slot='badge']" }),
    ).toBeInTheDocument();
  });

  it("shows empty state when no messages", async () => {
    server.use(
      http.get("/api/messages", () => HttpResponse.json(emptyMessages)),
    );
    renderDashboard();
    await screen.findByText(/no messages yet/i);
  });

  it("deletes a message after confirmation", async () => {
    server.use(
      http.delete("/api/messages/1", () =>
        HttpResponse.json({ message: "Message deleted" }),
      ),
    );

    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText("Bank");

    const deleteButtons = screen.getAllByLabelText("Delete message");
    await user.click(deleteButtons[0]);

    await screen.findByText("Delete message", {
      selector: "[data-slot='alert-dialog-title']",
    });

    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.queryByText("Bank")).not.toBeInTheDocument();
    });
  });

  it("regenerates webhook token, shows loader, and closes dialog", async () => {
    const newWebhook = {
      webhook_url: "http://localhost:8001/api/webhook/new-token-456",
      webhook_token: "new-token-456",
    };
    let resolveRegenerate: ((value: typeof newWebhook) => void) | undefined;
    server.use(
      http.post(
        "/api/settings/webhook/regenerate",
        () =>
          new Promise((resolve) => {
            resolveRegenerate = (value) => resolve(HttpResponse.json(value));
          }),
      ),
    );

    const user = userEvent.setup();
    renderDashboard();

    await screen.findByDisplayValue(mockWebhook.webhook_url);

    await user.click(screen.getByLabelText("Regenerate token"));

    await screen.findByText("Regenerate token", {
      selector: "[data-slot='alert-dialog-title']",
    });

    await user.click(screen.getByRole("button", { name: "Regenerate" }));

    const regeneratingButton = await screen.findByRole("button", {
      name: /regenerating/i,
    });
    expect(regeneratingButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();

    resolveRegenerate!(newWebhook);

    await screen.findByDisplayValue(newWebhook.webhook_url);
    await waitFor(() => {
      expect(
        screen.queryByText("Regenerate token", {
          selector: "[data-slot='alert-dialog-title']",
        }),
      ).not.toBeInTheDocument();
    });
  });

  it("shows pagination with page numbers when there are multiple pages", async () => {
    server.use(
      http.get("/api/messages", () =>
        HttpResponse.json({
          messages: mockMessages.messages,
          total: 10,
          page: 1,
          page_size: 5,
        }),
      ),
    );
    renderDashboard();

    const page1 = await screen.findByRole("button", { name: "1" });
    expect(page1).toHaveAttribute("aria-current", "page");

    const page2 = screen.getByRole("button", { name: "2" });
    expect(page2).not.toHaveAttribute("aria-current", "page");

    expect(screen.getByLabelText("Go to previous page")).toBeDisabled();
    expect(screen.getByLabelText("Go to next page")).toBeEnabled();
  });

  it("navigates to page 2 when page 2 button is clicked", async () => {
    server.use(
      http.get("/api/messages", ({ request }) => {
        const url = new URL(request.url);
        const requestedPage = Number(url.searchParams.get("page") ?? 1);
        if (requestedPage === 2) {
          return HttpResponse.json({
            messages: [
              {
                id: 3,
                sender: "Page2Sender",
                content: "Page 2 message",
                received_at: "2026-06-21T12:00:00Z",
                category: null,
                created_at: "2026-06-21T12:00:00Z",
              },
            ],
            total: 10,
            page: 2,
            page_size: 5,
          });
        }
        return HttpResponse.json({
          messages: mockMessages.messages,
          total: 10,
          page: 1,
          page_size: 5,
        });
      }),
    );

    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText("Bank");
    await user.click(screen.getByRole("button", { name: "2" }));

    await screen.findByText("Page2Sender");
  });

  it("does not show pagination when all messages fit on one page", async () => {
    renderDashboard();
    await screen.findByText("Bank");
    expect(
      screen.queryByLabelText("Go to previous page"),
    ).not.toBeInTheDocument();
  });

  it("shows ellipsis for many pages", async () => {
    server.use(
      http.get("/api/messages", () =>
        HttpResponse.json({
          messages: mockMessages.messages,
          total: 50,
          page: 1,
          page_size: 5,
        }),
      ),
    );
    renderDashboard();

    await screen.findByRole("button", { name: "1" });
    expect(screen.getByText("More pages")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
  });

  it("has search input and category filter", async () => {
    renderDashboard();
    await screen.findByPlaceholderText("Search messages...");
    expect(screen.getByLabelText("Filter by category")).toBeInTheDocument();
  });

  it("shows category filter trigger with All label", async () => {
    renderDashboard();
    const trigger = await screen.findByLabelText("Filter by category");
    expect(trigger.textContent).toContain("All");
  });
});
