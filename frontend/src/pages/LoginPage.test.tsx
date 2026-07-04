import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import LoginPage from "@/pages/LoginPage";
import { renderWithQueryClient } from "@/test-utils";

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderWithQueryClient(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("renders link to register page", () => {
    renderWithQueryClient(<LoginPage />);
    const link = screen.getByRole("link", { name: /register/i });
    expect(link).toHaveAttribute("href", "/register");
  });

  it("shows error toast on failed login", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          { detail: "Invalid email or password" },
          { status: 401 },
        ),
      ),
    );
    const user = userEvent.setup();

    renderWithQueryClient(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrongpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeInTheDocument();
    });
  });

  it("navigates to home on successful login", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json({
          id: 1,
          name: "Test User",
          email: "test@example.com",
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
    const user = userEvent.setup();

    renderWithQueryClient(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
  });
});
