import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { BrowserRouter } from "react-router-dom";

import GuestRoute from "@/components/GuestRoute";
import { server } from "@/mocks/server";
import { mockUser } from "@/test-utils";

function renderGuestRoute() {
  return render(
    <BrowserRouter>
      <GuestRoute>
        <div>Guest Content</div>
      </GuestRoute>
    </BrowserRouter>,
  );
}

describe("GuestRoute", () => {
  it("renders children when unauthenticated", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "Not authenticated" }, { status: 401 }),
      ),
    );

    renderGuestRoute();

    await waitFor(() => {
      expect(screen.getByText("Guest Content")).toBeInTheDocument();
    });
  });

  it("redirects to home when authenticated", async () => {
    server.use(http.get("/api/auth/me", () => HttpResponse.json(mockUser)));

    renderGuestRoute();

    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
  });

  it("shows loading state while checking auth", () => {
    server.use(http.get("/api/auth/me", () => new Promise<Response>(() => {})));

    renderGuestRoute();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
