import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DashboardPage from "@/pages/DashboardPage";
import {
  mockFetchSequence,
  mockUser,
  renderWithOutletContext,
} from "@/test-utils";

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
  page_size: 20,
};

const emptyMessages = { messages: [], total: 0, page: 1, page_size: 20 };

function renderDashboard(messagesOverride = mockMessages) {
  mockFetchSequence(
    { status: 200, body: mockWebhook },
    { status: 200, body: mockCategories },
    { status: 200, body: messagesOverride },
  );
  return renderWithOutletContext(<DashboardPage />, { user: mockUser });
}

describe("DashboardPage", () => {
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
    renderDashboard(emptyMessages);
    await screen.findByText(/no messages yet/i);
  });

  it("deletes a message after confirmation", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText("Bank");

    const deleteButtons = screen.getAllByLabelText("Delete message");
    await user.click(deleteButtons[0]);

    await screen.findByText("Delete message", {
      selector: "[data-slot='alert-dialog-title']",
    });

    mockFetchSequence(
      { status: 200, body: { message: "Message deleted" } },
      {
        status: 200,
        body: {
          messages: [mockMessages.messages[1]],
          total: 1,
          page: 1,
          page_size: 20,
        },
      },
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.queryByText("Bank")).not.toBeInTheDocument();
    });
  });

  it("regenerates webhook token after confirmation", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByDisplayValue(mockWebhook.webhook_url);

    await user.click(screen.getByLabelText("Regenerate token"));

    await screen.findByText("Regenerate token", {
      selector: "[data-slot='alert-dialog-title']",
    });

    const newWebhook = {
      webhook_url: "http://localhost:8001/api/webhook/new-token-456",
      webhook_token: "new-token-456",
    };
    mockFetchSequence({ status: 200, body: newWebhook });

    await user.click(screen.getByRole("button", { name: "Regenerate" }));

    await screen.findByDisplayValue(newWebhook.webhook_url);
  });

  it("shows pagination when needed", async () => {
    const paginatedMessages = {
      messages: mockMessages.messages,
      total: 40,
      page: 1,
      page_size: 20,
    };
    renderDashboard(paginatedMessages);

    await screen.findByText("Page 1 of 2");
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
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
