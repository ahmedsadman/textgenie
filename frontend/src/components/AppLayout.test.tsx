import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import AppLayout from "@/components/AppLayout";
import { mockFetch, mockUser } from "@/test-utils";

function renderLayout() {
  return render(
    <BrowserRouter>
      <AppLayout />
      <Toaster />
    </BrowserRouter>,
  );
}

describe("AppLayout", () => {
  it("redirects to login when unauthenticated", async () => {
    mockFetch(401, { detail: "Not authenticated" });

    renderLayout();

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });

  it("renders sidebar with nav items when authenticated", async () => {
    mockFetch(200, mockUser);

    renderLayout();

    await waitFor(() => {
      expect(screen.getAllByText("TextGenie").length).toBeGreaterThan(0);
    });
    expect(
      screen.getByRole("link", { name: /dashboard/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /categories/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
  });

  it("logs out and redirects to login", async () => {
    mockFetch(200, mockUser);

    renderLayout();

    await waitFor(() => {
      expect(screen.getAllByText("TextGenie").length).toBeGreaterThan(0);
    });

    mockFetch(200, { message: "Logged out successfully" });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /logout/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });

  it("shows loading state while checking auth", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValueOnce(new Promise(() => {}));

    renderLayout();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
