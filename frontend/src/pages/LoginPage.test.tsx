import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import LoginPage from "@/pages/LoginPage";
import { mockFetch, renderWithRouter } from "@/test-utils";

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderWithRouter(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("renders link to register page", () => {
    renderWithRouter(<LoginPage />);
    const link = screen.getByRole("link", { name: /register/i });
    expect(link).toHaveAttribute("href", "/register");
  });

  it("shows error toast on failed login", async () => {
    mockFetch(401, { detail: "Invalid email or password" });
    const user = userEvent.setup();

    renderWithRouter(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrongpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeInTheDocument();
    });
  });

  it("navigates to home on successful login", async () => {
    mockFetch(200, {
      id: 1,
      name: "Test User",
      email: "test@example.com",
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();

    renderWithRouter(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
  });
});
