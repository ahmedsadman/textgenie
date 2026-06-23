import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import AppLayout from "@/components/AppLayout";
import { server } from "@/mocks/server";
import { mockUser } from "@/test-utils";

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
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "Not authenticated" }, { status: 401 }),
      ),
    );

    renderLayout();

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });

  it("renders sidebar with nav items when authenticated", async () => {
    server.use(http.get("/api/auth/me", () => HttpResponse.json(mockUser)));

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
    server.use(
      http.get("/api/auth/me", () => HttpResponse.json(mockUser)),
      http.post("/api/auth/logout", () =>
        HttpResponse.json({ message: "Logged out successfully" }),
      ),
    );

    renderLayout();

    await waitFor(() => {
      expect(screen.getAllByText("TextGenie").length).toBeGreaterThan(0);
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /logout/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });

  it("shows loading state while checking auth", () => {
    server.use(http.get("/api/auth/me", () => new Promise<Response>(() => {})));

    renderLayout();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
