import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DashboardPage from "@/pages/DashboardPage";
import { renderWithRouter } from "@/test-utils";

const mockUser = {
  id: 1,
  name: "Test User",
  email: "test@example.com",
  created_at: "2026-01-01T00:00:00Z",
};

function mockFetch(status: number, body: Record<string, unknown>) {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

describe("DashboardPage", () => {
  it("shows user name when authenticated", async () => {
    mockFetch(200, mockUser);

    renderWithRouter(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/test user/i)).toBeInTheDocument();
    });
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("redirects to login when unauthenticated", async () => {
    mockFetch(401, { detail: "Not authenticated" });

    renderWithRouter(<DashboardPage />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });

  it("logs out and redirects to login", async () => {
    mockFetch(200, mockUser);

    renderWithRouter(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/test user/i)).toBeInTheDocument();
    });

    mockFetch(200, { message: "Logged out successfully" });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /logout/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });
});
