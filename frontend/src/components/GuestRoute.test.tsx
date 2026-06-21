import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";

import GuestRoute from "@/components/GuestRoute";
import { mockFetch, mockUser } from "@/test-utils";

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
    mockFetch(401, { detail: "Not authenticated" });

    renderGuestRoute();

    await waitFor(() => {
      expect(screen.getByText("Guest Content")).toBeInTheDocument();
    });
  });

  it("redirects to home when authenticated", async () => {
    mockFetch(200, mockUser);

    renderGuestRoute();

    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
  });

  it("shows loading state while checking auth", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValueOnce(new Promise(() => {}));

    renderGuestRoute();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
